from django.shortcuts import render
from lib.f5_api_reqs import get_custom_f5_stats, delete_custom_f5_cache
from django.http import JsonResponse, HttpResponse, HttpResponseServerError


# Create your views here.

def cache_page(request):
    return render(request, 'cache_page.html')


def create_cache_stats_json(request):
    cache_stats_dict = get_custom_f5_stats()
    if cache_stats_dict is not None:
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


def delete_cache(request):
    delete_cache_result = delete_custom_f5_cache()
    if delete_cache_result is not None:
        return HttpResponse("All objects in cache is cleared.")
    else:
        return HttpResponseServerError("Failed to delete cache!")
