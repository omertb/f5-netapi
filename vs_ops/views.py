from django.shortcuts import render
import json
from lib.f5_api_reqs import f5_custom_create_vs, f5_custom_create_pool
from lib.f5_api_reqs import f5_create_vs, f5_create_pool
import re
import time
from nw_restapi.settings import config
import logging
from . models import VServer
from django.http import JsonResponse
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe


logger = logging.getLogger(__name__)


def get_client_ip(req):
    x_forwarded_for = req.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[-1]
    else:
        client_ip = req.META.get("REMOTE_ADDR")
    return client_ip


def vs_page(request):
    load_balancers = {}
    for lb_name, lb_addr in config['F5_LB_LIST'].items():
        load_balancers[lb_name.upper()] = lb_addr
    if request.method == "POST":
        ValidIpAddressRegex = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        ValidPortRegex = r"^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4}))$"
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
        lb_desc = request.POST.get("lbDescription")
        if persistence == "none":
            persistence = None

        username = request.POST.get("adUser")
        password = request.POST.get("adPass")
        lb_addr = request.POST.get("vsLoadBalancerSelect")

        # Validations
        valid_str_re = r"^[A-Za-z0-9_\.\-]+$"
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
        if not re.compile(valid_str_re).match(lb_desc):
            errors.append("Failed for LB Description: Valid Characters: A-Z, a-z, 0-9, -(dash), _(underscore) and .(dot)")
        if not re.compile(valid_str_re).match(vs_name):
            errors.append("Failed for VS Name : Valid Characters: A-Z, a-z, 0-9, -(dash), _(underscore) and .(dot)")
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
        client_ip = get_client_ip(request)
        if response is not None:
            if response.status_code == 409:
                msg = f"Pool {svc_pool_name} already exists"
                logger.info(f"{client_ip} - {username} - Creating service pool response: {msg}")
                errors.append(msg)
            elif response.status_code == 200:
                msg = f"Pool {svc_pool_name} is created."
                logger.info(f"{client_ip} - {username} - Creating service pool response: {msg}")
                success.append(msg)
            else:
                msg = f"Failed to create {svc_pool_name}; Response Code: {response.status_code}, {response.text}"
                logger.info(f"{client_ip} - {username} - Creating service pool response: {msg}")
                errors.append(msg)
        else:
            msg = f"Unknown error for creating pool {svc_pool_name}"
            logger.info(f"{client_ip} - {username} - Creating service pool response: {msg}")
            errors.append(msg)
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
                    msg = f"Pool {waf_pool_name} already exists"
                    logger.info(f"{client_ip} - {username} - Creating waf pool response: {msg}")
                    errors.append(msg)
                elif response.status_code == 200:
                    msg = f"Pool {waf_pool_name} is created."
                    logger.info(f"{client_ip} - {username} - Creating waf pool response: {msg}")
                    success.append(msg)
                else:
                    msg = f"Failed to create pool {waf_pool_name}; Response Code: {response.status_code}, {response.text}"
                    logger.info(f"{client_ip} - {username} - Creating waf pool response: {msg}")
                    errors.append(msg)
            else:
                msg = f"Unknown error for creating pool {waf_pool_name}"
                logger.info(f"{client_ip} - {username} - Creating waf pool response: {msg}")
                errors.append(msg)
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
            response = f5_create_vs(lb_addr, username, password, waf_ret_vs_name, dest_ip, svc_pool_name, profiles, irule, lb_desc, snat, persistence)
            if response is not None:
                if response.status_code == 409:
                    msg = f"Virtual Server {waf_ret_vs_name} already exists"
                    logger.info(f"{client_ip} - {username} - Creating waf return VS Response: {msg}")
                    errors.append(msg)
                elif response.status_code == 200:
                    msg = f"Virtual Server {waf_ret_vs_name} is created."
                    logger.info(f"{client_ip} - {username} - Creating waf return VS Response: {msg}")
                    success.append(msg)
                else:
                    msg = f"Failed to create VS {waf_ret_vs_name}; Response Code: {response.status_code}, {response.text}"
                    logger.info(f"{client_ip} - {username} - Creating waf return VS Response: {msg}")
                    errors.append(msg)
            else:
                msg = f"Unknown error for creating VS {waf_ret_vs_name}"
                logger.info(f"{client_ip} - {username} - Creating waf return VS Response: {msg}")
                errors.append(msg)
        
        # create a http virtual server to redirect to https
        if redirect_https == "yes":
            http80_vs_name = f"{vs_name}_80"
            dest_ip = f"{vs_ip}:80"
            pool_name = None
            irule = "_sys_https_redirect"
            profiles = [
                { "name": "/Common/http_common", "context": "all" }
            ]
            response = f5_create_vs(lb_addr, username, password, http80_vs_name, dest_ip, pool_name, profiles, irule, lb_desc)
            if response is not None:
                if response.status_code == 409:
                    msg = f"Virtual Server {http80_vs_name} already exists"
                    logger.info(f"{client_ip} - {username} - Creating http-to-https VS Response: {msg}")
                    errors.append(msg)
                elif response.status_code == 200:
                    msg = f"Virtual Server {http80_vs_name} is created."
                    logger.info(f"{client_ip} - {username} - Creating http-to-https VS Response: {msg}")
                    success.append(msg)
                else:
                    msg = f"Failed to create VS {http80_vs_name}; Response Code: {response.status_code}, {response.text}"
                    logger.info(f"{client_ip} - {username} - Creating http-to-https VS Response: {msg}")
                    errors.append(msg)
            else:
                msg = f"Unknown error for creating VS {http80_vs_name}"
                logger.info(f"{client_ip} - {username} - Creating http-to-https VS Response: {msg}")
                errors.append(msg)
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
            response = f5_create_vs(lb_addr, username, password, ssl_vs_name, dest_ip, pool_name, profiles, irule, lb_desc, snat, persistence)
            if response is not None:
                if response.status_code == 409:
                    msg = f"Virtual Server {ssl_vs_name} already exists"
                    logger.info(f"{client_ip} - {username} - Creating SSL VS Response: {msg}")
                    errors.append(msg)
                elif response.status_code == 200:
                    msg = f"Virtual Server {ssl_vs_name} is created."
                    logger.info(f"{client_ip} - {username} - Creating SSL VS Response: {msg}")
                    success.append(msg)
                else:
                    msg = f"Failed to create VS {ssl_vs_name}; Response Code: {response.status_code}, {response.text}"
                    logger.info(f"{client_ip} - {username} - Creating SSL VS Response: {msg}")
                    errors.append(msg)
            else:
                msg = f"Unknown error for creating VS {ssl_vs_name}"
                logger.info(f"{client_ip} - {username} - Creating SSL VS Response: {msg}")
                errors.append(msg)
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
            response = f5_create_vs(lb_addr, username, password, nonssl_vs_name, dest_ip, svc_pool_name, profiles, irule, lb_desc, snat, persistence)
            if response is not None:
                if response.status_code == 409:
                    msg = f"Virtual Server {nonssl_vs_name} already exists"
                    logger.info(f"{client_ip} - {username} - Creating Non-Ssl VS Response: {msg}")
                    errors.append(msg)
                elif response.status_code == 200:
                    msg = f"Virtual Server {nonssl_vs_name} is created."
                    logger.info(f"{client_ip} - {username} - Creating Non-Ssl VS Response: {msg}")
                    success.append(msg)
                else:
                    msg = f"Failed to create VS {nonssl_vs_name}; Response Code: {response.status_code}, {response.text}"
                    logger.info(f"{client_ip} - {username} - Creating Non-Ssl VS Response: {msg}")
                    errors.append(msg)
            else:
                msg = f"Unknown error for creating VS {nonssl_vs_name}"
                logger.info(f"{client_ip} - {username} - Creating Non-Ssl VS Response: {msg}")
                errors.append(msg)
            if errors:
                return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})
        
        return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})

    return render(request, 'create_vs.html', {'load_balancers': load_balancers})


def virtuals(request):
    db_vservers = VServer.objects.all()
    response_json = []
    for db_vserver in db_vservers:
        vserver_dict = {
            'id': db_vserver.id,
            'lb': db_vserver.lb.name,
            'name' : db_vserver.name,
            'ip_addr': db_vserver.ip_addr,
            'port': db_vserver.port,
            'nat': db_vserver.nat,
            'persistence': db_vserver.persistence
        }
        if db_vserver.pool is not None:
            vserver_dict['pool'] = db_vserver.pool.name
            vserver_dict['lb_method'] = db_vserver.pool.lb_method
            vserver_dict['monitor'] = db_vserver.pool.monitor
            vserver_dict['pool_members'] = [
                {
                    'name': member['name'],
                    'ip_addr': member['ip_addr'],
                    'port': member['port'],
                    'state': member['state'],
                    'session': member['session']
                } for member in db_vserver.pool.member.values()
            ]
            member_html_list = []
            for member in vserver_dict['pool_members']:
                member_html = f"""
                    <a href="#" 
                        class="popover-trigger" 
                        data-bs-custom-class="custom-popover" 
                        data-bs-toggle="popover" 
                        data-bs-trigger="hover" 
                        data-bs-placement="auto" 
                        data-bs-html="true" 
                        data-bs-title="{member['name']}"
                        data-bs-content='
                        <div class="row">
                            <div class="row">
                                <div class="col-6"><strong>IP:</strong></div>
                                <div class="col-6">{member['ip_addr']}</div>
                            </div>
                            <div class="row">
                                <div class="col-6"><strong>Port:</strong></div>
                                <div class="col-6">{member['port']}</div>
                            </div>
                            <div class="row">
                                <div class="col-6"><strong>State:</strong></div>
                                <div class="col-6">{member['state']}</div>
                            </div>
                        </div>
                        '>
                        {member['name']}
                    </a>
                """
                member_html_list.append(member_html)
            vserver_dict['members'] = ', '.join(member_html_list)
        else:
            vserver_dict['pool'] = None
            vserver_dict['lb_method'] = None
            vserver_dict['monitor'] = None
            vserver_dict['pool_members'] = None
            vserver_dict['members'] = None
        irules = [{irule['name']: irule['content']} for irule in db_vserver.irule.values()]
        irules_html_list = []
        for irule in irules:
            irule_html = f"""
                <a href="#" 
                class="tooltip-trigger" 
                data-bs-custom-class="custom-tooltip" 
                data-bs-toggle="tooltip" 
                data-bs-trigger="hover focus" 
                data-bs-placement="auto" 
                data-bs-html="false" 
                data-bs-title="{escape(list(irule.values())[0])}">
                {list(irule.keys())[0]}
                </a>
            """
            #irule_html = f'<a href="#" class="popover-trigger" data-bs-custom-class="custom-popover" data-bs-toggle="popover" data-bs-trigger="hover" data-bs-placement="auto" data-bs-html="true" data-bs-title="iRule Code" data-bs-content="{escape(list(irule.values())[0])}">{list(irule.keys())[0]}</a>'
            irules_html_list.append(irule_html)
        vserver_dict['irules'] = ', '.join(irules_html_list)
        vserver_dict['policies'] = ', '.join([policy['name'] for policy in db_vserver.policy.values()])
        vserver_dict['profiles'] = ', '.join([profile['name'] for profile in db_vserver.profile.values()])
        response_json.append(vserver_dict)
    return JsonResponse(response_json, safe=False)

def show_vs(request):
    return render(request, 'show_vs.html')