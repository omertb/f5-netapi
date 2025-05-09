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


def f5_create_vs(host, user, passwd, vs_name, vs_ip, pool_name, profiles, irule, descr, snat="none", persistence=None):
    create_vs_api_url = f"https://{host}/mgmt/tm/ltm/virtual"
    payload = {
        "name": vs_name,
        "destination": vs_ip,
        "description": descr,
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
    
    return f5_api_request("POST", create_vs_api_url, user, passwd, data=json.dumps(payload))


def f5_custom_create_vs(vs_name, vs_ip, pool_name, profiles, irule, snat="none", persistence=None):
    return f5_create_vs(F5_HOST, F5_USER, F5_PASS, vs_name, vs_ip, pool_name, profiles, irule, snat, persistence)


def f5_save_sys_config(host, user, passwd):
    save_config_url = f"https://{host}/mgmt/tm/sys/config"
    payload = {
            "command": "save"
    }
    return f5_api_request("POST", save_config_url, user, passwd, data=json.dumps(payload))


def f5_create_pool(host, user, passwd, pool_name, members, lb_method):
    create_pool_api_url = f"https://{host}/mgmt/tm/ltm/pool"
    payload = {
            "name": pool_name,
            "monitor": "/Common/tcp",
            "members": members,
            "loadBalancingMode": lb_method
    }
    return f5_api_request("POST", create_pool_api_url, user, passwd, data=json.dumps(payload))


def f5_custom_create_pool(pool_name, members, lb_method):
    return f5_create_pool(F5_HOST, F5_USER, F5_PASS, pool_name, members, lb_method)


def f5_get_client_ssl_profiles(host, user, passwd):
    client_ssl_profiles_api_url = f"https://{host}/mgmt/tm/ltm/profile/client-ssl"
    return f5_api_request("GET", client_ssl_profiles_api_url, user, passwd)


def f5_custom_get_client_ssl_profiles(lb_host):
    response = f5_get_client_ssl_profiles(lb_host, F5_USER, F5_PASS)
    if response:
        if response.status_code == 200:
            result = json.loads(response.text)
            name_list = [profile['name'] for profile in result['items']]
            return name_list
        else:
            return None
    else:
        return None


def f5_get_cache_status(host, user, passwd):
    cache_profile = "~Common~webaccel_common"
    cache_status_api_url = f"https://{host}/mgmt/tm/ltm/profile/web-acceleration/{cache_profile}/stats"
    response = f5_api_request("GET", cache_status_api_url, user, passwd)
    if response is not None:
        if response.status_code == 200:
            result = json.loads(response.text)
            cache_stats_dict = list(result['entries'].values())[-1]['nestedStats']['entries']
            return cache_stats_dict
        else:
            return None
    else:
        return None


def get_custom_f5_stats(lb_host):
    return f5_get_cache_status(lb_host, F5_USER, F5_PASS)


def f5_delete_cache(host, user, passwd):
    delete_cache_api_url = f"https://{host}/mgmt/tm/ltm/profile/ramcache/all"
    response = f5_api_request("DELETE", delete_cache_api_url, user, passwd)
    if response.status_code == 200:
        return "SUCCESS"
    else:
        return None


def delete_custom_f5_cache(lb_host, username, password):
    return f5_delete_cache(lb_host, username, password)


def f5_import_pfx_cert(host, user, passwd, filename, passphrase):
    F5_DOWNLOAD_ROOT = "/var/config/rest/downloads"
    upload_cert_api_url = f"https://{host}/mgmt/tm/sys/crypto/pkcs12"
    file_location = f"{F5_DOWNLOAD_ROOT}/{filename}"

    payload = json.dumps({
        "command": "install",
        "name": filename,
        "from-local-file": file_location,
        "passphrase": passphrase
        })
    response = f5_api_request("POST", upload_cert_api_url, user, passwd, data=payload)
    return response.status_code, response.text


def f5_custom_import_pfx_cert(filename):
    return f5_import_pfx_cert(F5_HOST, F5_USER, F5_PASS, filename, "12345678")


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


def f5_create_ssl_profile(host, user, passwd, profile_name, certname, keyname, ecdhe):
    payload = {}
    payload['name'] = profile_name
    payload['cert'] = certname
    payload['key'] = keyname
    if ecdhe:
        payload["ciphers"] = "none"
        payload["cipherGroup"] = "/Common/yapikredi_ecdhe"
    create_ssl_profile_api_url =  f"https://{host}/mgmt/tm/ltm/profile/client-ssl"
    response = f5_api_request("POST", create_ssl_profile_api_url, user, passwd, data=json.dumps(payload))
    if response is not None:
        return response.status_code
    else:
        return None


def f5_custom_create_ssl_profile(pfx_certname):
    return f5_create_ssl_profile(F5_HOST, F5_USER, F5_PASS, pfx_certname, pfx_certname)


def get_vservers(lb_ip):
    get_vservers_url = f"https://{lb_ip}/mgmt/tm/ltm/virtual"
    response = f5_api_request("GET", get_vservers_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)['items']
        else:
            return None
    else:
        return None


def get_pool_members(lb_ip, pool_name):
    get_pool_members_url = f"https://{lb_ip}/mgmt/tm/ltm/pool/{pool_name}/members"
    response = f5_api_request("GET", get_pool_members_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)['items']
        else:
            return None
    else:
        return None

def get_pool(lb_ip, pool_name):
    get_pool_url = f"https://{lb_ip}/mgmt/tm/ltm/pool/{pool_name}"
    response = f5_api_request("GET", get_pool_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return None
    else:
        return None

def get_vserver_policies(lb_ip, vs_name):
    get_vserver_policy_url = f"https://{lb_ip}/mgmt/tm/ltm/virtual/{vs_name}/policies"
    response = f5_api_request("GET", get_vserver_policy_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)['items']
        else:
            return None
    else:
        return None


def get_vserver_profiles(lb_ip, vs_name):
    get_vserver_profiles_url = f"https://{lb_ip}/mgmt/tm/ltm/virtual/{vs_name}/profiles"
    response = f5_api_request("GET", get_vserver_profiles_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)['items']
        else:
            return None
    else:
        return None


def get_irule(lb_ip, irule_name):
    get_irule_url = f"https://{lb_ip}/mgmt/tm/ltm/rule/{irule_name}"
    response = f5_api_request("GET", get_irule_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return None
    else:
        return None