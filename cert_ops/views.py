from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from lib.f5_api_reqs import f5_custom_import_pfx_cert, f5_custom_file_upload, f5_custom_create_ssl_profile, f5_custom_get_client_ssl_profiles
from lib.f5_api_reqs import f5_import_pfx_cert, f5_file_upload, f5_create_ssl_profile, f5_custom_get_client_ssl_profiles
import time
from nw_restapi.settings import config

def cert_page(request):
    load_balancers = {}
    for lb_name, lb_addr in config['F5_LB_LIST'].items():
        load_balancers[lb_name.upper()] = lb_addr
    
    if 'certfile' in request.FILES:
        if request.method == 'POST' and request.FILES['certfile']:
            certfile = request.FILES['certfile']
            lb_addr = request.POST.get('loadBalancerSelect')
            username = request.POST.get("adUser")
            password = request.POST.get("adPass")
            pfx_passphrase = request.POST.get("pfxPassphrase")
            if pfx_passphrase == "":
                pfx_passphrase = "12345678"
            fs = FileSystemStorage()
            filename = fs.save(certfile.name, certfile)

            uresult = f5_file_upload(lb_addr, username, password, certfile.name)
            if uresult == 200:
                upload_result = "Success"
            else:
                upload_result = "FAILED"

            iresult = f5_import_pfx_cert(lb_addr, username, password, certfile.name, pfx_passphrase)
            if iresult == 200:
                import_result = "Success"
            else:
                import_result = "FAILED"
            
            sslresult = f5_create_ssl_profile(lb_addr, username, password, certfile.name, certfile.name)
            if sslresult == 200:
                profile_name = f'{certfile.name.replace(".pfx", "").replace(".tr", "").replace(".com", "").replace(".yapikredi", "")}_{time.strftime("%d_%m_%Y")}'
                clientssl_result = f"Success"
            else:
                profile_name = ""
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
    name_list = f5_custom_get_client_ssl_profiles()
    if name_list is not None:
        return JsonResponse(name_list, safe=False)