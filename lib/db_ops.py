from vs_ops.models import LoadBalancer, Member, Pool, IRule, Policy, Profile, VServer
from lib.f5_api_reqs import get_vservers, get_pool, get_pool_members, get_irule, get_vserver_policies, get_vserver_profiles
from nw_restapi.settings import config
import time
from datetime import datetime


def get_create_pool_members_db(lb_ip, lb_id, pool_name):
    pool_members = get_pool_members(lb_ip, pool_name)
    if pool_members is None:
        return None
    current_members = []
    for member in pool_members:
        try:
            db_member = Member.objects.get(name=member['name'], pool_name=pool_name, lb_id=lb_id)
            current_members.append(db_member)
        except Member.DoesNotExist:
            member_db_values = {
                'name': member['name'],
                'ip_addr': member['address'],
                'port': member['name'].split(':')[-1],
                'pool_name': pool_name,
                'lb_id': lb_id,
                'state': member['state'],
                'monitor': member['monitor'],
                'session': member['session']
            }
            new_member = Member(**member_db_values)
            new_member.save()
            current_members.append(new_member)
    return current_members

def get_create_vserver_pool_db(lb_ip, lb_id, pool_name):
    try:
        db_pool = Pool.objects.get(name=pool_name, lb_id=lb_id)
    except Pool.DoesNotExist:
        pool = get_pool(lb_ip, pool_name)
        if pool is None:
            return None
        pool_db_values = {
            'name': pool['name'],
            'lb_id': lb_id,
            'lb_method': pool['loadBalancingMode'],
            'monitor': pool['monitor'].split('/')[-1]
        }
        db_pool = Pool(**pool_db_values)
    db_pool.save()
    pool_members = get_create_pool_members_db(lb_ip, lb_id, pool_name)
    db_pool.member.set(pool_members)
    db_pool.save()
    return db_pool.id


def create_irules_db(lb_ip, lb_id, rules):
    db_irules = []
    for rule in rules:
        rule_name = rule.split('/')[-1]
        result = get_irule(lb_ip, rule_name)
        IRULE_EXISTS = IRule.objects.filter(name=rule_name, lb_id=lb_id)
        if IRULE_EXISTS:
            db_irule = IRULE_EXISTS.get()
            db_irule.content = result['apiAnonymous']   
        else:
            db_irule = IRule(name=rule_name, lb_id=lb_id, content=result['apiAnonymous'])
        db_irule.save()
        db_irules.append(db_irule)
    return db_irules


def create_vserver_policies_db(lb_ip, lb_id, vs_name):
    db_policies = []
    policies = get_vserver_policies(lb_ip, vs_name)
    if policies is not None:
        for policy in policies:
            POLICY_EXISTS = Policy.objects.filter(name=policy['name'], lb_id=lb_id)
            if POLICY_EXISTS:
                db_policy = POLICY_EXISTS.get()
            else:
                db_policy = Policy(name=policy['name'], lb_id=lb_id)
                db_policy.save()
            db_policies.append(db_policy)
    return db_policies


def create_vserver_profiles_db(lb_ip, lb_id, vs_name):
    db_profiles = []
    profiles = get_vserver_profiles(lb_ip, vs_name)
    if profiles is not None:
        for profile in profiles:
            PROFILE_EXISTS = Profile.objects.filter(name=profile['name'], lb_id=lb_id)
            if PROFILE_EXISTS:
                db_profile = PROFILE_EXISTS.get()
                db_profile.context = profile['context']
            else:
                db_profile = Profile(name=profile['name'], lb_id=lb_id, context=profile['context'])
            db_profile.save()
            db_profiles.append(db_profile)
    return db_profiles

def create_update_vs_table(lb_ip, lb_id):
    vservers = get_vservers(lb_ip)
    db_vservers = VServer.objects.filter(lb_id=lb_id)
    if vservers is not None:
        f5_vserver_lb_list = []
        for vserver in vservers:
            f5_vserver_lb_list.append(f"{vserver['name']}-{lb_ip}")
            VS_EXISTS = VServer.objects.filter(name=vserver['name'], lb_id=lb_id)
            if VS_EXISTS:
                db_vserver = VS_EXISTS.get()  # convert queryset to single item
                db_last_modified = db_vserver.last_modified
                api_last_modified = datetime.fromisoformat(vserver['lastModifiedTime'])
                if db_last_modified != api_last_modified:
                    if 'pool' in vserver:
                        pool_name = vserver['pool'].split('/')[-1]
                        if db_vserver.pool is None:
                            pool_id = get_create_vserver_pool_db(lb_ip, lb_id, pool_name)
                            db_vserver.pool_id = pool_id
                        elif db_vserver.pool.name != pool_name:
                            pool_id = get_create_vserver_pool_db(lb_ip, lb_id, pool_name)
                            db_vserver.pool_id = pool_id
                        else:
                            pool_id = db_vserver.pool_id
                    else:
                        pool_id = None
                    #
                    vsip, vsport = vserver['destination'].split('/')[-1].split(':')
                    vserver_db_values = {
                        'name': vserver['name'],
                        'ip_addr': vsip,
                        'port': vsport,
                        'nat': vserver['sourceAddressTranslation']['type'],
                        'persistence': ', '.join([persistence['name'] for persistence in vserver['persist']]) if 'persist' in vserver else None,
                        'lb_id': lb_id,
                        'pool_id': pool_id,
                        'description': vserver['description'] if 'description' in vserver else None,
                        'last_modified': vserver['lastModifiedTime']
                    }
                    for key, value in vserver_db_values.items():
                        setattr(db_vserver, key, value)
                    db_vserver.save()         
            else:
                vsip, vsport = vserver['destination'].split('/')[-1].split(':')
                if 'pool' in vserver:
                    pool_name = vserver['pool'].split('/')[-1]
                    pool_id = get_create_vserver_pool_db(lb_ip, lb_id, pool_name)
                else:
                    pool_id = None
                vserver_db_values = {
                    'name': vserver['name'],
                    'ip_addr': vsip,
                    'port': vsport,
                    'nat': vserver['sourceAddressTranslation']['type'],
                    'persistence': ', '.join([persistence['name'] for persistence in vserver['persist']]) if 'persist' in vserver else None,
                    'lb_id': lb_id,
                    'pool_id': pool_id,
                    'description': vserver['description'] if 'description' in vserver else None,
                    'last_modified': vserver['lastModifiedTime']
                }
                db_vserver = VServer(**vserver_db_values)
                db_vserver.save()
            
            if 'rules' in vserver:
                irules = create_irules_db(lb_ip, lb_id, vserver['rules'])
            else:
                irules = []
            policies = create_vserver_policies_db(lb_ip, lb_id, vserver['name'])
            profiles = create_vserver_profiles_db(lb_ip, lb_id, vserver['name'])
            db_vserver.irule.set(irules)
            db_vserver.policy.set(policies)
            db_vserver.profile.set(profiles)

            db_vserver.save()
        for db_vserver in db_vservers:
            vserver_lb_ip = f"{db_vserver.name}-{db_vserver.lb.ip_addr}"
            if vserver_lb_ip not in f5_vserver_lb_list:
                db_vserver.delete()
            

def create_update_lb_table():
    ip_addrs = []
    for lb_name, lb_addr in config['F5_LB_LIST'].items():
        LB_EXISTS = LoadBalancer.objects.filter(ip_addr=lb_addr)
        if not LB_EXISTS:
            LB_EXISTS_WITH_SAME_NAME = LoadBalancer.objects.filter(name=lb_name)
            if LB_EXISTS_WITH_SAME_NAME:
                lb_name = f"{lb_name}-{lb_addr}"
            lb_db = LoadBalancer.objects.create(name=lb_name, ip_addr=lb_addr)
        ip_addrs.append(lb_addr)
    
    db_lbs = LoadBalancer.objects.all()
    for lb in db_lbs:
        if lb.ip_addr not in ip_addrs:
            lb.delete()
        else:
            create_update_vs_table(lb.ip_addr, lb.id)
        

def main():
    t1 = time.perf_counter()
    create_update_lb_table()
    print(round(time.perf_counter() - t1, 3))


if __name__ == '__main__':
    main()