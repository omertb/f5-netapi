from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from lib.f5_api_reqs import f5_custom_import_pfx_cert, f5_custom_file_upload, f5_custom_create_ssl_profile, f5_custom_get_client_ssl_profiles
import time
# Create your views here.

def cert_page(request):
    if 'certfile' in request.FILES:
        if request.method == 'POST' and request.FILES['certfile']:
            certfile = request.FILES['certfile']
            username = request.POST.get("adUser")
            password = request.POST.get("adPass")
            return render(request, 'cert_upload.html')
            fs = FileSystemStorage()
            filename = fs.save(certfile.name, certfile)

            uresult = f5_custom_file_upload(certfile.name)
            if uresult == 200:
                upload_result = "Success."
            else:
                upload_result = "FAILED!"

            iresult = f5_custom_import_pfx_cert(certfile.name)
            if iresult == 200:
                import_result = "Success."
            else:
                import_result = "FAILED!"
            
            sslresult = f5_custom_create_ssl_profile(certfile.name)
            if sslresult == 200:
                profile_name = f'{certfile.name.replace(".pfx", "").replace(".tr", "").replace(".com", "").replace(".yapikredi", "")}_{time.strftime("%d_%m_%Y")}'
                clientssl_result = f"Success."
            else:
                profile_name = ""
                clientssl_result = "FAILED!"

            return render(request, 'cert_upload.html', {
                    'upload_result': upload_result,
                    'import_result': import_result,
                    'clientssl_result': clientssl_result,
                    'profile_name': profile_name
                })
    return render(request, 'cert_upload.html')


def get_ssl_profiles(request):
    name_list = f5_custom_get_client_ssl_profiles()
    if name_list is not None:
        return JsonResponse(name_list, safe=False)