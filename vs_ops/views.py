from django.shortcuts import render
import json
from lib.f5_api_reqs import f5_custom_create_vs, f5_custom_create_pool
import re

# Create your views here.

def vs_page(request):
    if request.method == "POST":
        ValidIpAddressRegex = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        ValidPortRegex = "^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4}))$"
        errors = []
        success = []
        # get form values
        vs_name = request.POST.get("vsName")
        ssl_profile = request.POST.get("sslProfile")
        vs_ip = request.POST.get("vsIpAddr")
        waf_svc_ip = request.POST.get("wafSvcIpAddr")
        waf_return_ip = request.POST.get("wafRetIpAddr")
        svc_ip_list = request.POST.getlist("serv_ip[]")
        svc_ip_list = list(filter(None, svc_ip_list))  # remove emtpy items
        svc_port_list = request.POST.getlist("serv_port[]")
        svc_port_list = list(filter(None, svc_port_list))
        lb_method = request.POST.get("lbMethodSelect")
        persistence = request.POST.get("persistenceSelect")
        # Validations
        if not (vs_name and vs_ip and waf_svc_ip and waf_return_ip and svc_ip_list and svc_port_list and ssl_profile):
            return render(request, 'create_vs.html', {'errors': ["All fields are required!"]})
        if not re.search(ValidIpAddressRegex, vs_ip):
            errors.append(f"Invalid IP Address : {vs_ip}")
        if not re.search(ValidIpAddressRegex, waf_svc_ip):
            errors.append(f"Invalid IP Address : {waf_svc_ip}")
        if not re.search(ValidIpAddressRegex, waf_return_ip):
            errors.append(f"Invalid IP Address : {waf_return_ip}")
        if len(vs_name) < 4:
            errors.append(f"Too short for Virtual Server Name")
        for svc_ip in svc_ip_list:
            if not re.search(ValidIpAddressRegex, svc_ip):
                errors.append(f"Invalid IP Address : {svc_ip}")
        for svc_port in svc_port_list:
            if not re.search(ValidPortRegex, svc_port):
                errors.append(f"Invalid Port Number : {svc_port}")
        if errors:
            return render(request, 'create_vs.html', {'errors': errors})
        
        """
        [
            { "name": "/Common/tcp", "context": "all" },
            { "name": "/Common/http_common", "context": "all" },
            { "name": f"/Common/{sslprofile}", "context": "clientside" },
            { "name": "/Common/webaccel_common", "context": "all" },
            { "name": "/Common/qradar", "context": "all" }
        ]
        """

        ## create load balancer parameter variables

        # create WAF Service Pool
        waf_pool_name = f"{vs_name}_ssl"
        members = [f"{waf_svc_ip}:80"]
        waf_lb_method = "round-robin"
        response = f5_custom_create_pool(waf_pool_name, members, waf_lb_method)
        if response is not None:
            if response.status_code == 409:
                errors.append(f"Pool {waf_pool_name} already exists")
            elif response.status_code == 200:
                success.append(f"Pool {waf_pool_name} is created.")
            else:
                errors.append(f"Failed to create pool {waf_pool_name}; Response Code: {response.status_code}, {response.text}")
        else:
            errors.append(f"Unknown error for creating pool {waf_pool_name}")
        if errors:
            return render(request, 'create_vs.html', {'errors': errors, 'success': success})
        
        # create Backend Service Pool
        svc_pool_name = f"{vs_name}_ssl_waf"
        members = [f"{service}:{svc_port_list[idx]}" for idx, service in enumerate(svc_ip_list)]
        response = f5_custom_create_pool(svc_pool_name, members, lb_method)
        if response is not None:
            if response.status_code == 409:
                errors.append(f"Pool {svc_pool_name} already exists")
            elif response.status_code == 200:
                success.append(f"Pool {svc_pool_name} is created.")
            else:
                errors.append(f"Failed to create {svc_pool_name}; Response Code: {response.status_code}, {response.text}")
        else:
            errors.append(f"Unknown error for creating pool {svc_pool_name}")
        if errors:
            return render(request, 'create_vs.html', {'errors': errors, 'success': success})
        
        # http_80 virtual server
        http80_vs_name = f"{vs_name}_80"
        dest_ip = f"{vs_ip}:80"
        pool_name = None
        irule = "_sys_https_redirect"
        profiles = [
            { "name": "/Common/http_common", "context": "all" }
        ]
        response = f5_custom_create_vs(http80_vs_name, dest_ip, pool_name, profiles, irule)
        if response is not None:
            if response.status_code == 409:
                errors.append(f"Virtual Server {http80_vs_name} already exists")
            elif response.status_code == 200:
                success.append(f"Virtual Server {http80_vs_name} is created.")
            else:
                errors.append(f"Failed to create VS {http80_vs_name}; Response Code: {response.status_code}, {response.text}")
        else:
            errors.append(f"Unknown error for creating VS {http80_vs_name}")
        if errors:
            return render(request, 'create_vs.html', {'errors': errors, 'success': success})
        
        # ssl virtual server
        ssl_vs_name = f"{vs_name}_ssl"
        dest_ip = f"{vs_ip}:443"
        irule = "irule_backup_vs"
        profiles = [
            { "name": "/Common/http_common", "context": "all" },
            { "name": f"/Common/{ssl_profile}", "context": "clientside" },
            { "name": "/Common/webaccel_common", "context": "all" },
            { "name": "/Common/qradar", "context": "all" }
        ]
        response = f5_custom_create_vs(ssl_vs_name, dest_ip, waf_pool_name, profiles, irule)
        if response is not None:
            if response.status_code == 409:
                errors.append(f"Virtual Server {ssl_vs_name} already exists")
            elif response.status_code == 200:
                success.append(f"Virtual Server {ssl_vs_name} is created.")
            else:
                errors.append(f"Failed to create VS {ssl_vs_name}; Response Code: {response.status_code}, {response.text}")
        else:
            errors.append(f"Unknown error for creating VS {ssl_vs_name}")
        if errors:
            return render(request, 'create_vs.html', {'errors': errors, 'success': success})

        
        # waf return virtual server
        waf_ret_vs_name = f"{vs_name}_ssl_waf"
        dest_ip = f"{waf_return_ip}:80"
        irule = "irule_ins_client_XFF"
        snat = "automap"
        profiles = [
            { "name": "/Common/tcp", "context": "all" },
            { "name": "/Common/http", "context": "all" }
        ]
        if persistence == "none":
            persistence = None
        response = f5_custom_create_vs(waf_ret_vs_name, dest_ip, svc_pool_name, profiles, irule, snat, persistence)
        if response is not None:
            if response.status_code == 409:
                errors.append(f"Virtual Server {waf_ret_vs_name} already exists")
            elif response.status_code == 200:
                success.append(f"Virtual Server {waf_ret_vs_name} is created.")
            else:
                errors.append(f"Failed to create VS {waf_ret_vs_name}; Response Code: {response.status_code}, {response.text}")
        else:
            errors.append(f"Unknown error for creating VS {waf_ret_vs_name}")
        
        return render(request, 'create_vs.html', {'errors': errors, 'success': success})



    return render(request, 'create_vs.html')