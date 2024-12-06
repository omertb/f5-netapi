#from f5_api_reqs import f5_api_reqs, get_pool_members
import requests
from requests.auth import HTTPBasicAuth
import json
import configparser
from pathlib import Path
import os

from pprint import pprint


# suppress certificate verification warnings
requests.packages.urllib3.disable_warnings()

# CONSTANT INPUT VALUES from CONFIG FILE
BASE_DIR = Path(__file__).resolve().parent.parent
COMMON_CONFIG_FILE = os.path.join(BASE_DIR, 'common.config')
config = configparser.ConfigParser()
config.read(COMMON_CONFIG_FILE)
F5_USER = config.get('F5', 'user')
F5_PASS = config.get('F5', 'pass')

F5_LBS = {}
for lb_name, nodes in config['F5_NODE_IPS'].items():
    NODE1, NODE2 = nodes.split(',')
    F5_LBS[lb_name] = {
        'node1': NODE1,
        'node2': NODE2
    }


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

def get_pools(lb_ip):
    get_pools_url = f"https://{lb_ip}/mgmt/tm/ltm/pool"
    response = f5_api_request("GET", get_pools_url, F5_USER, F5_PASS)
    if response is not None:
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return None
    else:
        return None


def get_diff_states():
    node1_members_status = {}
    node2_members_status = {}
    for lb_name, lb_nodes in F5_LBS.items():
        node1_pools = get_pools(lb_nodes['node1'])
        node2_pools = get_pools(lb_nodes['node2'])
        if node1_pools is None or node2_pools is None:
            print(f"Error: one of nodes of {lb_name} does not return pools!")
            return
        else:
            for item in node1_pools['items']:
                pool_members_1 = get_pool_members(lb_nodes['node1'], item['name'])
                pool_members_2 = get_pool_members(lb_nodes['node2'], item['name'])
                if pool_members_1 is None or pool_members_2 is None:
                    print(f"{item['name'] } pool members could not be fetched on {lb_name}!")
                    return
                else:
                    for member_item in pool_members_1:
                        node1_members_status[f"{lb_name}--{member_item['name']}"] = member_item['state']
                    for member_item in pool_members_2:
                        node2_members_status[f"{lb_name}--{member_item['name']}"] = member_item['state']


    members_with_diff_states = []
    members = list(zip(node1_members_status.items(), node2_members_status.items()))
    for member in members:
        if member[0][0] != member[1][0]:
            print(f"Services are not same: {member[0][0]}, {member[1][0]}")
            continue
        else:
            if member[0][1] != member[1][1]:
                lb_name, member_name = member[0][0].split('--')
                members_with_diff_states.append({
                    'name': member_name,
                    'node1_state': member[0][1].upper(),
                    'node2_state': member[1][1].upper(),
                    'lb_name': lb_name
                })
    return members_with_diff_states


def main():
    members_with_diff_states = get_diff_states()
    if members_with_diff_states is not None:
        for member in members_with_diff_states:
            print(f"{member['name']:<30} Node1: {member['node1_state']:<12} Node2: {member['node2_state']:<12} LB: {member['lb_name']}")


if __name__ == '__main__':
    main()