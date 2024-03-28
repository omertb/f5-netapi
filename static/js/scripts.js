// wait animation with wait-modal
$body = $("body");
$(document).on({
    ajaxStart: function() { $body.addClass("loading");    },
     ajaxStop: function() { $body.removeClass("loading"); }
});

let $cacheStatsTable = $('#cacheStatsTable');
$(document).on("click", "#getCacheStatsButton" , function(event){
    $.ajax({
        type: "GET",
        url: "/cache/stats.json",
        success: function(response_data){
            $cacheStatsTable.bootstrapTable("destroy");
            $cacheStatsTable.bootstrapTable({data: response_data});
        }
    });
});

let clearCacheResult = document.getElementById("clearCacheResult");
$(document).on("click", "#clearCacheButton" , function(event){
    $.ajax({
        type: "GET",
        url: "/cache/delete",
        success: function(response_data){
            $cacheStatsTable.bootstrapTable("destroy");
            clearCacheResult.innerHTML = '<div class="mt-4 text-center alert alert-warning">' + response_data + '</div>';
        },
        error: function(response_data){
            clearCacheResult.innerHTML = '<div class="mt-4 text-center alert alert-danger">' + response_data.responseText + '</div>';
        }
    });
});
$(document).on("click", "#clearCacheModalClose", function(event){
    clearCacheResult.innerHTML = "";
});

let loadBalancerSelectCache = document.getElementById("vsLoadBalancerSelectCache");
document.addEventListener("DOMContentLoaded", function() { 
    let selected_lb = loadBalancerSelectCache.value;
    $.ajaxSetup({
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    });
    $.ajax({
        type: "POST",
        url: "/cache/stats.json",
        data: selected_lb,
        success: function(data) {
            $cacheStatsTable.bootstrapTable("destroy");
            $cacheStatsTable.bootstrapTable({data: data});
            errorDiv.innerHTML = "";
            errorDiv.removeAttribute("class")
        },
        error: function(data) {
            $cacheStatsTable.bootstrapTable("destroy");
            $('#errorDiv').addClass('alert alert-danger');
            errorDiv.innerHTML = data.responseJSON.message;
        }
    });
    /*
    fetch("/cache/stats.json", {
        method: "POST",
        body: selected_lb,
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    })
    .then(response => {
        if (!response.ok) {
            let err = new Error("Cache stats could not be fetched for  " + selected_lb + " " + response.status);
            err.response = response;
            err.status = response.status;
            throw err;
        }
        return response.json();
    })
    .then(responseJson => {
        console.log(responseJson);
        $cacheStatsTable.bootstrapTable("destroy");
        $cacheStatsTable.bootstrapTable({data: responseJson});
        errorDiv.innerHTML = "";
        errorDiv.removeAttribute("class")
    })
    .catch(err => {
        $('#errorDiv').addClass('alert alert-danger');
        errorDiv.innerHTML = err.message;
    });*/
});

loadBalancerSelectCache.addEventListener("change", function(){
    $cacheStatsTable.bootstrapTable("destroy");
    let selected_lb = loadBalancerSelectCache.value;
    $.ajaxSetup({
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    });
    $.ajax({
        type: "POST",
        url: "/cache/stats.json",
        data: selected_lb,
        success: function(data) {
            $cacheStatsTable.bootstrapTable("destroy");
            $cacheStatsTable.bootstrapTable({data: data});
            errorDiv.innerHTML = "";
            errorDiv.removeAttribute("class")
        },
        error: function(data) {
            $cacheStatsTable.bootstrapTable("destroy");
            $('#errorDiv').addClass('alert alert-danger');
            errorDiv.innerHTML = data.responseJSON.message;
        }
    });
    /*
    fetch("/cache/stats.json", {
        method: "POST",
        body: selected_lb,
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    })
    .then(response => {
        if (!response.ok) {
            let err = new Error("Cache stats could not be fetched for  " + selected_lb + " " + response.status);
            err.response = response;
            err.status = response.status;
            throw err;
        }
        return response.json();
    })
    .then(responseJson => {
        console.log(responseJson);
        $cacheStatsTable.bootstrapTable("destroy");
        $cacheStatsTable.bootstrapTable({data: responseJson});
        errorDiv.innerHTML = "";
        errorDiv.removeAttribute("class")
    })
    .catch(err => {
        $('#errorDiv').addClass('alert alert-danger');
        errorDiv.innerHTML = err.message;
    });*/
});

$(document).ready(function() {
    // Check if the table has any rows
    if ($('tbody tr').length == 0) {
        // Hide the table header and toolbar content
        $('thead').hide();
    }
});
