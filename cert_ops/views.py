from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from lib.f5_api_reqs import f5_custom_import_pfx_cert, f5_custom_file_upload, f5_custom_create_ssl_profile, f5_custom_get_client_ssl_profiles
from lib.f5_api_reqs import f5_import_pfx_cert, f5_file_upload, f5_create_ssl_profile, f5_custom_get_client_ssl_profiles
import time
from nw_restapi.settings import config
import json
import re
import logging


logger = logging.getLogger(__name__)


def get_client_ip(req):
    x_forwarded_for = req.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[-1]
    else:
        client_ip = req.META.get("REMOTE_ADDR")
    return client_ip



def cert_page(request):
    load_balancers = {}
    for lb_name, lb_addr in config['F5_LB_LIST'].items():
        load_balancers[lb_name.upper()] = lb_addr
    
    if 'certfile' in request.FILES:
        if request.method == 'POST' and request.FILES['certfile']:
            client_ip = get_client_ip(request)
            certfile = request.FILES['certfile']

            if certfile.name.split(".")[-1] != "pfx":
                msg = "File should be in pfx format!"
                return render(request, 'cert_upload.html', {'load_balancers': load_balancers, 'error': msg})
            # check certificate name against valid characters
            valid_str_re = "^[A-Za-z0-9_\.]+$"
            if not re.compile(valid_str_re).match(certfile.name):
                msg = "Failed : Valid Characters: A-Z, a-z, 0-9, _(underscore) and .(dot)"
                return render(request, 'cert_upload.html', {'load_balancers': load_balancers, 'error': msg})
            
            lb_addr = request.POST.get('loadBalancerSelect')
            username = request.POST.get("adUser")
            password = request.POST.get("adPass")
            pfx_passphrase = request.POST.get("pfxPassphrase")
            create_same_as_filename = request.POST.get("fileNameCheck")
            ecdhe_check = request.POST.get("ecdheCheck")
            if pfx_passphrase == "":
                pfx_passphrase = "12345678"
            
            fs = FileSystemStorage()
            if create_same_as_filename == "yes":
                certname = certfile.name
            else:
                certfile.name = certfile.name.replace(".yapikredi.com.tr.pfx", ".pfx").replace(".com.tr.pfx", ".pfx").replace(".tr.pfx", ".pfx").replace(".com.pfx", ".pfx")
                certname = re.sub(r'\.pfx$', f'_{time.strftime("%d_%m_%Y")}.pfx', certfile.name)
            filename = fs.save(certname, certfile)

            uresult = f5_file_upload(lb_addr, username, password, certname)
            if uresult == 200:
                logger.info(f"{client_ip} - {username} - File: {certname} upload is successful.")
                upload_result = "Success"
            else:
                logger.info(f"{client_ip} - {username} - File: {certname} upload is FAILED.")
                upload_result = "FAILED"

            iresult = f5_import_pfx_cert(lb_addr, username, password, certname, pfx_passphrase)
            if iresult == 200:
                logger.info(f"{client_ip} - {username} - Pfx: {certname} import is successful.")
                import_result = "Success"
            else:
                logger.info(f"{client_ip} - {username} - Pfx: {certname} import FAILED.")
                import_result = "FAILED"

            profile_name = re.sub(r'\.pfx$', '', certname)
            if ecdhe_check == "yes":
                ecdhe = True
            else:
                ecdhe = False
            sslresult = f5_create_ssl_profile(lb_addr, username, password, profile_name, certname, certname, ecdhe)
            if sslresult == 200:
                logger.info(f"{client_ip} - {username} - SSL Client Profile: {profile_name} creation is successful.")
                clientssl_result = f"Success"
            else:
                logger.info(f"{client_ip} - {username} - SSL Client Profile: {profile_name} creation FAILED.")
                clientssl_result = "FAILED"

            return render(request, 'cert_upload.html', {
                    'upload_result': upload_result,
                    'import_result': import_result,
                    'clientssl_result': clientssl_result,
                    'profile_name': profile_name,
                    'load_balancers': load_balancers,
                    "lb_addr": lb_addr
                })

    return render(request, 'cert_upload.html', {'load_balancers': load_balancers})


def get_ssl_profiles(request):
    if request.method == 'POST':
        client_ip = get_client_ip(request)
        lb_host = request.body.decode()
        name_list = f5_custom_get_client_ssl_profiles(lb_host)
        if name_list is not None:
            logger.info(f"{client_ip} - Called get_ssl_profiles for LB: {lb_host} successfully.")
            return JsonResponse(name_list, safe=False)
        else:
            logger.info(f"{client_ip} - Calling get_ssl_profiles for LB: {lb_host} FAILED.")
        