from django.shortcuts import render
from lib.f5_api_reqs import get_custom_f5_stats, delete_custom_f5_cache
from django.http import JsonResponse, HttpResponse, HttpResponseServerError
from nw_restapi.settings import config
import json
import logging


logger = logging.getLogger(__name__)


def get_client_ip(req):
    x_forwarded_for = req.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[-1]
    else:
        client_ip = req.META.get("REMOTE_ADDR")
    return client_ip


def cache_page(request):
    load_balancers = {}
    for lb_name, lb_addr in config['F5_LB_LIST'].items():
        load_balancers[lb_name.upper()] = lb_addr
    return render(request, 'cache_page.html', {'load_balancers': load_balancers})


def create_cache_stats_json(request):
    client_ip = get_client_ip(request)
    if request.method == 'POST':
        lb_host = request.body.decode()
        cache_stats_dict = get_custom_f5_stats(lb_host)
        if cache_stats_dict is not None:
            msg = f"{client_ip} - Viewed Cache Stats for {lb_host} successfully."
            logger.info(msg)
            response_json = [
                {
                    'cache_count': cache_stats_dict['cacheCount']['value'],
                    'cache_hits': cache_stats_dict['cacheHits']['value'],
                    'cache_hit_bytes': cache_stats_dict['cacheHitBytes']['value'],
                    'cache_misses': cache_stats_dict['cacheMissesAll']['value'],
                    'cache_miss_bytes': cache_stats_dict['cacheMissBytesAll']['value'],
                    'cache_size': cache_stats_dict['cacheSize']['description']
                }
            ]
            return JsonResponse(response_json, safe=False)
        else:
            msg = f"{client_ip} - Viewing Cache Stats for {lb_host} FAILED."
            logger.info(msg)


def delete_cache(request):
    if request.method == 'POST':
        client_ip = get_client_ip(request)
        credentials = json.loads(request.body)
        if credentials['username'] == "" or credentials['password'] == "":
            message = "Enter your username, password please"
            return HttpResponseServerError(message)
            #return JsonResponse({'message':message}, status=400)
        else:
            delete_cache_result = delete_custom_f5_cache(credentials['selected_lb'], credentials['username'], credentials['password'])
            if delete_cache_result is not None:
                msg = "All objects in cache is cleared."
                logger.info(f"{client_ip} - User: {credentials['username']} - {msg}")
                return HttpResponse(msg)
            else:
                msg = "Failed to delete cache!"
                logger.info(f"{client_ip} - User: {credentials['username']} - {msg}")
                return HttpResponseServerError(msg)
            #return JsonResponse("SUCCESS", safe=False)
    #delete_cache_result = delete_custom_f5_cache()
    #if delete_cache_result is not None:
    #    return HttpResponse("All objects in cache is cleared.")
    #else:
    #    return HttpResponseServerError("Failed to delete cache!")
