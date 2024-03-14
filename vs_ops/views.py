from django.shortcuts import render
import json
from lib.f5_api_reqs import f5_custom_create_vs, f5_custom_create_pool
from lib.f5_api_reqs import f5_create_vs, f5_create_pool
import re
import time
from nw_restapi.settings import config

# Create your views here.

def vs_page(request):
    load_balancers = {}
    for lb_name, lb_addr in config['F5_LB_LIST'].items():
        load_balancers[lb_name.upper()] = lb_addr
    if request.method == "POST":
        ValidIpAddressRegex = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        ValidPortRegex = "^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4}))$"
        errors = []
        success = []
        # get form values
        vs_name = request.POST.get("vsName")
        config_type = request.POST.get("vServerConfigSelect")
        ssl_profile = request.POST.get("sslProfile")
        redirect_https = request.POST.get("redirectHttpsCheck")
        vs_ip = request.POST.get("vsIpAddr")
        vs_port = request.POST.get("vsPort")
        waf_svc_ip = request.POST.get("wafSvcIpAddr")
        waf_return_ip = request.POST.get("wafRetIpAddr")
        svc_ip_list = request.POST.getlist("serv_ip[]")
        svc_ip_list = list(filter(None, svc_ip_list))  # remove emtpy items
        svc_port_list = request.POST.getlist("serv_port[]")
        svc_port_list = list(filter(None, svc_port_list))
        svc_proto = request.POST.get("serviceProtoSelect")
        lb_method = request.POST.get("lbMethodSelect")
        persistence = request.POST.get("persistenceSelect")
        if persistence == "none":
            persistence = None

        username = request.POST.get("adUser")
        password = request.POST.get("adPass")
        lb_addr = request.POST.get("vsLoadBalancerSelect")

        # Validations
        if config_type == "waf":
            if not (vs_name and vs_ip and waf_svc_ip and waf_return_ip and svc_ip_list and svc_port_list and ssl_profile):
                return render(request, 'create_vs.html', {'errors': ["All fields are required!"], 'load_balancers': load_balancers})
            if not re.search(ValidIpAddressRegex, waf_svc_ip):
                errors.append(f"Invalid IP Address : {waf_svc_ip}")
            if not re.search(ValidIpAddressRegex, waf_return_ip):
                errors.append(f"Invalid IP Address : {waf_return_ip}")
        if config_type == "http" or config_type == "tcp"  or config_type == "ssl":
            if not (vs_name and vs_ip and svc_ip_list and svc_port_list):
                return render(request, 'create_vs.html', {'errors': ["All fields are required!"], 'load_balancers': load_balancers})
            if not re.search(ValidIpAddressRegex, vs_ip):
                errors.append(f"Invalid IP Address : {vs_ip}")
        if config_type == "ssl":
            if not (ssl_profile):
                return render(request, 'create_vs.html', {'errors': ["All fields are required!"], 'load_balancers': load_balancers})
        if len(vs_name) < 4:
            errors.append(f"Too short for Virtual Server Name")
        for svc_ip in svc_ip_list:
            if not re.search(ValidIpAddressRegex, svc_ip):
                errors.append(f"Invalid IP Address : {svc_ip}")
        for svc_port in svc_port_list:
            if not re.search(ValidPortRegex, svc_port):
                errors.append(f"Invalid Port Number : {svc_port}")
        if errors:
            return render(request, 'create_vs.html', {'errors': errors, 'load_balancers': load_balancers})
        
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

        # create Backend Service Pool
        if config_type == "waf":
            svc_pool_name = f"{vs_name}_ssl_waf"
        else:
            svc_pool_name = f"{vs_name}_pool"
        
        members = [f"{service}:{svc_port_list[idx]}" for idx, service in enumerate(svc_ip_list)]
        response = f5_create_pool(lb_addr, username, password, svc_pool_name, members, lb_method)
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
            return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})

        if config_type == "waf":
            # create WAF Service Pool
            waf_pool_name = f"{vs_name}_ssl"
            members = [f"{waf_svc_ip}:80"]
            waf_lb_method = "round-robin"
            response = f5_create_pool(lb_addr, username, password, waf_pool_name, members, waf_lb_method)
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
                return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})
            
            # waf return virtual server
            waf_ret_vs_name = f"{vs_name}_ssl_waf"
            dest_ip = f"{waf_return_ip}:80"
            irule = "irule_ins_client_XFF"
            snat = "automap"
            profiles = [
                { "name": "/Common/tcp", "context": "all" },
                { "name": "/Common/http", "context": "all" }
            ]
            if svc_proto == "ssl":
                profiles.append({ "name": f"/Common/serverssl", "context": "serverside" })
            response = f5_create_vs(lb_addr, username, password, waf_ret_vs_name, dest_ip, svc_pool_name, profiles, irule, snat, persistence)
            if response is not None:
                if response.status_code == 409:
                    errors.append(f"Virtual Server {waf_ret_vs_name} already exists")
                elif response.status_code == 200:
                    success.append(f"Virtual Server {waf_ret_vs_name} is created.")
                else:
                    errors.append(f"Failed to create VS {waf_ret_vs_name}; Response Code: {response.status_code}, {response.text}")
            else:
                errors.append(f"Unknown error for creating VS {waf_ret_vs_name}")
        
        # create a http virtual server to redirect to https
        if redirect_https == "yes":
            http80_vs_name = f"{vs_name}_80"
            dest_ip = f"{vs_ip}:80"
            pool_name = None
            irule = "_sys_https_redirect"
            profiles = [
                { "name": "/Common/http_common", "context": "all" }
            ]
            response = f5_create_vs(lb_addr, username, password, http80_vs_name, dest_ip, pool_name, profiles, irule)
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
                return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})
        
        # create ssl virtual server
        if config_type == "waf" or config_type == "ssl":
            # ssl virtual server
            ssl_vs_name = f"{vs_name}_ssl"
            dest_ip = f"{vs_ip}:{vs_port}"
            profiles = [
                { "name": "/Common/http_common", "context": "all" },
                { "name": f"/Common/{ssl_profile}", "context": "clientside" },
                { "name": "/Common/webaccel_common", "context": "all" },
                { "name": "/Common/qradar", "context": "all" }
            ]
            if svc_proto == "ssl":
                profiles.append({ "name": f"/Common/serverssl", "context": "serverside" })
            if config_type == "waf":
                irule = "irule_backup_vs"
                snat = "none"
                pool_name = waf_pool_name
            if config_type == "ssl":
                irule = "irule_ins_client_XFF"
                snat = "automap"
                pool_name = svc_pool_name
            response = f5_create_vs(lb_addr, username, password, ssl_vs_name, dest_ip, pool_name, profiles, irule, snat, persistence)
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
                return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})

        # create http or tcp virtual server with application services backend pool
        if config_type == "http" or config_type == "tcp":
            nonssl_vs_name = f"{vs_name}_{vs_port}"
            dest_ip = f"{vs_ip}:{vs_port}"
            irule = None
            snat = "automap"
            profiles = [
                { "name": "/Common/tcp", "context": "all" }
            ]
            if config_type == "http":
                irule = "irule_ins_client_XFF"
                profiles.append({ "name": "/Common/http_common", "context": "all" })
                profiles.append({ "name": "/Common/webaccel_common", "context": "all" })
                profiles.append({ "name": "/Common/qradar", "context": "all" })
            if svc_proto == "ssl":
                profiles.append({ "name": f"/Common/serverssl", "context": "serverside" })
            response = f5_create_vs(lb_addr, username, password, nonssl_vs_name, dest_ip, svc_pool_name, profiles, irule, snat, persistence)
            if response is not None:
                if response.status_code == 409:
                    errors.append(f"Virtual Server {nonssl_vs_name} already exists")
                elif response.status_code == 200:
                    success.append(f"Virtual Server {nonssl_vs_name} is created.")
                else:
                    errors.append(f"Failed to create VS {nonssl_vs_name}; Response Code: {response.status_code}, {response.text}")
            else:
                errors.append(f"Unknown error for creating VS {nonssl_vs_name}")
            if errors:
                return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})
        
        return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})

    return render(request, 'create_vs.html', {'load_balancers': load_balancers})