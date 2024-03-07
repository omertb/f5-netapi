import requests
from requests.auth import HTTPBasicAuth
import configparser
import json
import base64
import os
import time
from nw_restapi.settings import MEDIA_ROOT

from nw_restapi.settings import COMMON_CONFIG_FILE

config = configparser.ConfigParser()
config.read(COMMON_CONFIG_FILE)
F5_HOST = config.get('F5', 'host')
F5_USER = config.get('F5', 'user')
F5_PASS = config.get('F5', 'pass')

# suppress certificate verification warnings
requests.packages.urllib3.disable_warnings()


def f5_api_request(method, api_url, user, password, data=None):
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request(method, api_url, headers=headers, auth=HTTPBasicAuth(user, password), verify=False, data=data)
        return response
    except Exception as e:
        print(e)
        return None


def f5_create_vs(host, vs_name, vs_ip, pool_name, profiles, irule, snat, persistence):
    create_vs_api_url = f"https://{host}/mgmt/tm/ltm/virtual"
    print(snat)
    payload = {
        "name": vs_name,
        "destination": vs_ip,
        "ipProtocol": "tcp",
        "sourceAddressTranslation": { "type": snat },
        "profiles": profiles
    }

    if irule is not None:
        payload["rules"] = [ f"/Common/{irule}" ]

    if pool_name is not None:
        payload["pool"] = pool_name

    if persistence is not None:
        payload['persist'] = [
            {
                "name": persistence,
                "partition": "Common",
                "tmDefault": "yes",
            }
        ]
    
    return f5_api_request("POST", create_vs_api_url, F5_USER, F5_PASS, data=json.dumps(payload))


def f5_custom_create_vs(vs_name, vs_ip, pool_name, profiles, irule, snat="none", persistence=None):
    return f5_create_vs(F5_HOST, vs_name, vs_ip, pool_name, profiles, irule, snat, persistence)


def f5_create_pool(host, pool_name, members, lb_method):
    create_pool_api_url = f"https://{host}/mgmt/tm/ltm/pool"
    payload = {
            "name": pool_name,
            "monitor": "/Common/tcp",
            "members": members,
            "loadBalancingMode": lb_method
    }
    return f5_api_request("POST", create_pool_api_url, F5_USER, F5_PASS, data=json.dumps(payload))


def f5_custom_create_pool(pool_name, members, lb_method):
    return f5_create_pool(F5_HOST, pool_name, members, lb_method)


def f5_get_client_ssl_profiles(host):
    client_ssl_profiles_api_url = f"https://{host}/mgmt/tm/ltm/profile/client-ssl"
    return f5_api_request("GET", client_ssl_profiles_api_url, F5_USER, F5_PASS)


def f5_custom_get_client_ssl_profiles():
    response = f5_get_client_ssl_profiles(F5_HOST)
    if response:
        if response.status_code == 200:
            result = json.loads(response.text)
            name_list = [profile['name'] for profile in result['items']]
            return name_list
        else:
            return None
    else:
        return None


def f5_get_cache_status(host):
    cache_profile = "~Common~webaccel_common"
    cache_status_api_url = f"https://{host}/mgmt/tm/ltm/profile/web-acceleration/{cache_profile}/stats"
    response = f5_api_request("GET", cache_status_api_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            result = json.loads(response.text)
            cache_stats_dict = list(result['entries'].values())[-1]['nestedStats']['entries']
            return cache_stats_dict
        else:
            return None
    else:
        return None


def get_custom_f5_stats():
    return f5_get_cache_status(F5_HOST)


def f5_delete_cache(host):
    delete_cache_api_url = f"https://{host}/mgmt/tm/ltm/profile/ramcache/all"
    response = f5_api_request("DELETE", delete_cache_api_url, F5_USER, F5_PASS)
    if response.status_code == 200:
        return "SUCCESS"
    else:
        return None


def delete_custom_f5_cache():
    return f5_delete_cache(F5_HOST)


def f5_import_pfx_cert(host, filename):
    F5_DOWNLOAD_ROOT = "/var/config/rest/downloads"
    upload_cert_api_url = f"https://{host}/mgmt/tm/sys/crypto/pkcs12"
    file_location = f"{F5_DOWNLOAD_ROOT}/{filename}"

    payload = json.dumps({
        "command": "install",
        "name": filename,
        "from-local-file": file_location,
        "passphrase": "12345678"
        })
    response = f5_api_request("POST", upload_cert_api_url, F5_USER, F5_PASS, data=payload)
    return response.status_code


def f5_custom_import_pfx_cert(filename):
    return f5_import_pfx_cert(F5_HOST, filename=filename)


def f5_file_upload(host, user, password, filename):
    filepath = f"{MEDIA_ROOT}/{filename}"
    chunk_size = 512 * 1024
    headers = {
        'Content-Type': 'application/octet-stream'
    }
    fileobj = open(filepath, 'rb')
    filename = os.path.basename(filepath)

    # uploads to /var/config/rest/downloads/ in F5 disk
    uri = f"https://{host}/mgmt/shared/file-transfer/uploads/{filename}"
        
    requests.packages.urllib3.disable_warnings()
    size = os.path.getsize(filepath)

    start = 0

    while True:
        file_slice = fileobj.read(chunk_size)
        if not file_slice:
            break

        current_bytes = len(file_slice)
        if current_bytes < chunk_size:
            end = size
        else:
            end = start + current_bytes

        content_range = f"{start}-{end - 1}/{size}"
        headers['Content-Range'] = content_range
        result = requests.post(uri,
                      auth=HTTPBasicAuth(user, password),
                      data=file_slice,
                      headers=headers,
                      verify=False)

        start += current_bytes
        if result.status_code != 200:
            break
    return result.status_code


def f5_custom_file_upload(filename):
    return f5_file_upload(F5_HOST, F5_USER, F5_PASS, filename)


def f5_create_ssl_profile(host, certname, keyname):
    payload = {}
    payload['name'] = f'{certname.replace(".pfx", "").replace(".tr", "").replace(".com", "").replace(".yapikredi", "")}_{time.strftime("%d_%m_%Y")}'
    payload['cert'] = certname
    payload['key'] = keyname
    create_ssl_profile_api_url =  f"https://{host}/mgmt/tm/ltm/profile/client-ssl"
    response = f5_api_request("POST", create_ssl_profile_api_url, F5_USER, F5_PASS, data=json.dumps(payload))
    if response is not None:
        return response.status_code
    else:
        return None


def f5_custom_create_ssl_profile(pfx_certname):
    return f5_create_ssl_profile(F5_HOST, pfx_certname, pfx_certname)