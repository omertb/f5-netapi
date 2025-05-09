from django.shortcuts import render
import json
from lib.f5_api_reqs import f5_custom_create_vs, f5_custom_create_pool
from lib.f5_api_reqs import f5_create_vs, f5_create_pool, f5_save_sys_config
from lib.check_monitor_status import get_diff_states
import re
import time
from nw_restapi.settings import config
import logging
from . models import VServer
from django.http import JsonResponse, HttpResponseServerError
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.db.utils import OperationalError


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
        config_check = request.POST.get("genCommandsCheck")
        #logger.info(f"config_check: {str(config_checkbox)}, {type(config_checkbox)}")
        #return render(request, 'create_vs.html', {'errors': ['tugrul test'], 'load_balancers': load_balancers})
        ValidIpAddressRegex = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
        ValidPortRegex = r"^((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|([1-5][0-9]{4})|([0-5]{0,5})|([0-9]{1,4}))$"
        errors = []
        success = []
        commands = []
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
            if vs_port == "80" or vs_port == "443":
                svc_pool_name = f"{vs_name}_pool"
            else:
                svc_pool_name = f"{vs_name}_{vs_port}_pool"
        
        members = [f"{service}:{svc_port_list[idx]}" for idx, service in enumerate(svc_ip_list)]
        
        if config_check is None:
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
        
        else:  # config_check
            members_str = ""
            for member in members:
                member_ip, member_port = member.split(":")
                members_str += f" {member_ip}:{member_port} {{ address {member_ip} }}"
            commands.append(" # Services Pool Command:")
            commands.append(f"create ltm pool {svc_pool_name} {{  load-balancing-mode {lb_method}  members add {{ {members_str} }}  monitor tcp }}")


        if config_type == "waf":
            # create WAF Service Pool
            waf_pool_name = f"{vs_name}_ssl"
            members = [f"{waf_svc_ip}:80"]
            waf_lb_method = "round-robin"

            if config_check is None:
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
            
            else:
                members_str = ""
                for member in members:
                    member_ip, member_port = member.split(":")
                    members_str += f" {member_ip}:{member_port} {{ address {member_ip} }}"
                commands.append(" # Waf Pool Command:")
                commands.append(f"create ltm pool {waf_pool_name} {{  load-balancing-mode {waf_lb_method}  members add {{ {members_str} }}  monitor tcp }}")

            
            # waf return virtual server
            waf_ret_vs_name = f"{vs_name}_ssl_waf"
            dest_ip = f"{waf_return_ip}:80"
            irule = "irule_ins_client_XFF"
            snat = "automap"
            profiles = [
                { "name": "/Common/tcp", "context": "all" },
                { "name": "/Common/http", "context": "all" },
                { "name": "/Common/oneconnect_prefix32", "context": "all" }
            ]
            if svc_proto == "ssl":
                profiles.append({ "name": f"/Common/serverssl", "context": "serverside" })

            # modify persistence
            if persistence == "persist_cookie":
                modified_persistence = "persist_cookie_ssl_waf"
            elif persistence == "source_addr":
                modified_persistence = "persist_xff_uie_3600s"
            else:
                modified_persistence = None
            
            if config_check is None:
                response = f5_create_vs(lb_addr, username, password, waf_ret_vs_name, dest_ip, svc_pool_name, profiles, irule, lb_desc, snat, modified_persistence)
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
            
            else:  # config_check
                commands.append(" # Waf Return Vserver Command:")
                commands.append(f"create ltm virtual {waf_ret_vs_name} {{ description {lb_desc} "\
                                f"destination {dest_ip} ip-protocol tcp mask 255.255.255.255 "\
                                f"persist replace-all-with {{ {modified_persistence} {{ default yes }} }} "\
                                f"pool {svc_pool_name} profiles add {{ http {{ }} oneconnect_prefix32 {{ }} "\
                                f"tcp {{ }} }} rules {{ irule_ins_client_XFF }} "\
                                f"serverssl-use-sni disabled source 0.0.0.0/0 source-address-translation {{ type automap  }} "\
                                f"translate-address enabled translate-port enabled }}")
        
        # create a http virtual server to redirect to https
        if redirect_https == "yes":
            http80_vs_name = f"{vs_name}_80"
            dest_ip = f"{vs_ip}:80"
            pool_name = None
            irule = "_sys_https_redirect"
            profiles = [
                { "name": "/Common/http_common", "context": "all" }
            ]
            if config_check is None:
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
            else:  # config_check
                commands.append(" # Http Vserver Command:")
                commands.append(f"create ltm virtual {http80_vs_name} {{ description {lb_desc} "\
                                f"destination {dest_ip} ip-protocol tcp mask 255.255.255.255 "\
                                f"profiles add {{ http_common {{ }} "\
                                f"tcp {{ }} }} rules {{ _sys_https_redirect }} "\
                                f"serverssl-use-sni disabled source 0.0.0.0/0 "\
                                f"translate-address enabled translate-port enabled }}")
        
        # create ssl virtual server
        if config_type == "waf" or config_type == "ssl":
            # ssl virtual server
            ssl_vs_name = f"{vs_name}_ssl"
            dest_ip = f"{vs_ip}:{vs_port}"
            profiles = [
                { "name": "/Common/http_common", "context": "all" },
                { "name": f"/Common/{ssl_profile}", "context": "clientside" },
                { "name": "/Common/webaccel_common", "context": "all" },
                { "name": "/Common/httpcompression", "context": "all" },
                { "name": "/Common/qradar", "context": "all" },
                { "name": "/Common/oneconnect_prefix32", "context": "all" }
            ]
            snat = "automap"
            if svc_proto == "ssl":
                profiles.append({ "name": f"/Common/serverssl", "context": "serverside" })
            if config_type == "waf":
                irule = "irule_backup_vs"
                pool_name = waf_pool_name
            if config_type == "ssl":
                irule = "irule_ins_client_XFF"
                pool_name = svc_pool_name

            # modify persistence
            if persistence == "persist_cookie":
                modified_persistence = "persist_cookie_ssl"
            elif persistence == "source_addr":
                modified_persistence = "persist_xff_uie_3600s"
            else:
                modified_persistence = None
            
            if config_check is None:
                response = f5_create_vs(lb_addr, username, password, ssl_vs_name, dest_ip, pool_name, profiles, irule, lb_desc, snat, modified_persistence)
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
            else:  # config_check
                if config_type == "waf":
                    commands.append(" # SSL Vserver (before Waf) Command:")
                    commands.append(f"create ltm virtual {ssl_vs_name} {{ description {lb_desc} "\
                                    f"destination {dest_ip} ip-protocol tcp mask 255.255.255.255 "\
                                    f"persist replace-all-with {{ {modified_persistence} {{ default yes }} }} "\
                                    f"pool {pool_name} profiles add {{ http_common {{ }} oneconnect_prefix32 {{ }} "\
                                    f"qradar {{ }} webaccel_common {{ }} httpcompression {{ }} "\
                                    f"tcp {{ }} {ssl_profile} {{ context clientside }} }} rules {{ irule_backup_vs }} "\
                                    f"serverssl-use-sni disabled source 0.0.0.0/0 source-address-translation {{ type automap  }} "\
                                    f"translate-address enabled translate-port enabled }}")
                if config_type == "ssl":
                    commands.append(" # SSL Vserver Command:")
                    commands.append(f"create ltm virtual {ssl_vs_name} {{ description {lb_desc} "\
                                    f"destination {dest_ip} ip-protocol tcp mask 255.255.255.255 "\
                                    f"persist replace-all-with {{ {modified_persistence} {{ default yes }} }} "\
                                    f"pool {pool_name} profiles add {{ http_common {{ }} oneconnect_prefix32 {{ }} "\
                                    f"qradar {{ }} webaccel_common {{ }} httpcompression {{ }} "\
                                    f"tcp {{ }} {ssl_profile} {{ context clientside }} }} rules {{ irule_ins_client_XFF }} "\
                                    f"serverssl-use-sni disabled source 0.0.0.0/0 source-address-translation {{ type automap  }} "\
                                    f"translate-address enabled translate-port enabled }}")

        # create http or tcp virtual server with application services backend pool
        if config_type == "http" or config_type == "tcp":
            nonssl_vs_name = f"{vs_name}_{vs_port}"
            dest_ip = f"{vs_ip}:{vs_port}"
            irule = None
            snat = "automap"
            profiles = [
                { "name": "/Common/tcp", "context": "all" },
                { "name": "/Common/oneconnect_prefix32", "context": "all" }
            ]
            modified_persistence = persistence
            if config_type == "http":

                # modify persistence
                if persistence == "persist_cookie":
                    modified_persistence = "persist_cookie_ssl"
                elif persistence == "source_addr":
                    modified_persistence = "persist_xff_uie_3600s"
                else:
                    modified_persistence = None
                
                irule = "irule_ins_client_XFF"
                profiles.append({ "name": "/Common/http_common", "context": "all" })
                profiles.append({ "name": "/Common/webaccel_common", "context": "all" })
                profiles.append({ "name": "/Common/qradar", "context": "all" })
            if svc_proto == "ssl":
                profiles.append({ "name": f"/Common/serverssl", "context": "serverside" })
            if config_check is None:
                response = f5_create_vs(lb_addr, username, password, nonssl_vs_name, dest_ip, svc_pool_name, profiles, irule, lb_desc, snat, modified_persistence)
                if response is not None:
                    if response.status_code == 409:
                        msg = f"Virtual Server {nonssl_vs_name} already exists"
                        logger.info(f"{client_ip} - {username} - Creating Non-Ssl VS Response: {msg}")
                        errors.append(msg)
                    elif response.status_code == 200:
                        msg = f"Virtual Server {nonssl_vs_name} is created."
                        logger.info(f"{client_ip} - {username} - Creating Non-Ssl VS Response: {msg}")
                        logger.info(f"{response.text}")
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
            else:  # config_check
                if config_type == "http":
                    commands.append(" # HTTP Vserver (before Waf) Command:")
                    commands.append(f"create ltm virtual {nonssl_vs_name} {{ description {lb_desc} "\
                                    f"destination {dest_ip} ip-protocol tcp mask 255.255.255.255 "\
                                    f"persist replace-all-with {{ {modified_persistence} {{ default yes }} }} "\
                                    f"pool {svc_pool_name} profiles add {{ http_common {{ }} oneconnect_prefix32 {{ }} "\
                                    f"qradar {{ }} webaccel_common {{ }} httpcompression {{ }} "\
                                    f"tcp {{ }} }} rules {{ irule_ins_client_XFF }} "\
                                    f"serverssl-use-sni disabled source 0.0.0.0/0 source-address-translation {{ type automap  }} "\
                                    f"translate-address enabled translate-port enabled }}")
                if config_type == "tcp":
                    commands.append(" # TCP Vserver Command:")
                    commands.append(f"create ltm virtual {nonssl_vs_name} {{ description {lb_desc} "\
                                    f"destination {dest_ip} ip-protocol tcp mask 255.255.255.255 "\
                                    f"persist replace-all-with {{ {modified_persistence} {{ default yes }} }} "\
                                    f"pool {svc_pool_name} profiles add {{ oneconnect_prefix32 {{ }} tcp {{ }} }} "\
                                    f"serverssl-use-sni disabled source 0.0.0.0/0 source-address-translation {{ type automap  }} "\
                                    f"translate-address enabled translate-port enabled }}")
        
        if config_check is None:
            save_result = f5_save_sys_config(lb_addr, username, password)
            logger.info(f"{client_ip} - {username} - Saved config to {lb_addr}: {save_result}")
            return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'load_balancers': load_balancers})
        else:
            return render(request, 'create_vs.html', {'errors': errors, 'success': success, 'commands': commands, 'load_balancers': load_balancers})

    return render(request, 'create_vs.html', {'load_balancers': load_balancers})


def virtuals(request):
    response_json = []
    db_vservers = VServer.objects.all()

    for db_vserver in db_vservers:
        vserver_dict = {
            'id': db_vserver.id,
            'lb': db_vserver.lb.name,
            'name' : db_vserver.name,
            'ip_addr': db_vserver.ip_addr,
            'port': db_vserver.port,
            'nat': db_vserver.nat,
            'persistence': db_vserver.persistence,
            'description': db_vserver.description
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
        db_vserver_irules = db_vserver.irule.values()
        irules = [{irule['name']: irule['content']} for irule in db_vserver_irules]
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
        db_vserver_policies = db_vserver.policy.values()
        db_vserver_profiles = db_vserver.profile.values()
        vserver_dict['policies'] = ', '.join([policy['name'] for policy in db_vserver_policies])
        vserver_dict['profiles'] = ', '.join([profile['name'] for profile in db_vserver_profiles])
        response_json.append(vserver_dict)
    return JsonResponse(response_json, safe=False)

def show_vs(request):
    return render(request, 'show_vs.html')

def retrieve_member_states(request):
    # return table data in json format
    client_ip = get_client_ip(request)
    member_states = get_diff_states()
    if member_states is None:
        logger.info('Get member states returned None!')
        HttpResponseServerError(f"{client_ip} - Get member states returned None!")
    else:
        return JsonResponse(member_states, safe=False)

def member_states_diff(request):
    return render(request, 'member_states.html')
