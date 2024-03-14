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

// load clientssl profiles as datalist options on page Create VS
function delay(callback, ms) {
    var timer = 0;
    return function() {
      var context = this, args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () {
        callback.apply(context, args);
      }, ms || 0);
    };
  }

// disable button when submittin on create vs form
$(document).ready(function() {
    $("#createVSForm").submit(function() {
        $(".loading-icon").removeClass("visually-hidden");
        $("#createVSForm").attr("disabled", true);
        $("#createVSBtn").attr("disabled", true);
        $("#btnText").text("Submitting ...");
    });
});
    
$(document).ready(function() {
    // Check if the table has any rows
    if ($('tbody tr').length == 0) {
        // Hide the table header and toolbar content
        $('thead').hide();
    }
});


const searchInput = $("#searchContent");
const searchDatalist = $("#searchDatalistOptions");
let errorDiv = document.getElementById("errorDiv");
let loadBalancerSelect = document.getElementById("loadBalancerSelect");
document.addEventListener("DOMContentLoaded", function() { 
    let selected_lb = loadBalancerSelect.value;
    // clear previous options
    searchDatalist.empty();
    // load searchDatalist with ssl profiles
    fetch("/cert/sslprofiles.json", {
        method: "POST",
        body: selected_lb,
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    })
    .then(response => {
        if (!response.ok) {
            let err = new Error("SSL Profiles Could Not Be Fetched! " + response.status);
            err.response = response;
            err.status = response.status;
            throw err;
        }
        return response.json();
    })
    .then(responseJson => {
        responseJson.forEach(function(option) {
            searchDatalist.append(`<option value="${option}">`);
        });
        errorDiv.innerHTML = "";
        errorDiv.removeAttribute("class")
    })
    .catch(err => {
        $('#errorDiv').addClass('alert alert-danger');
        errorDiv.innerHTML = err.message;
    });
//} // endif
});

loadBalancerSelect.addEventListener("change", function(){
    // clear previous options
    searchDatalist.empty();
    let selected_lb = loadBalancerSelect.value;
    fetch("/cert/sslprofiles.json", {
        method: "POST",
        body: selected_lb,
        headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
        }
    })
    .then(response => {
        if (!response.ok) {
            let err = new Error("SSL Profiles Could Not Be Fetched! " + response.status);
            err.response = response;
            err.status = response.status;
            throw err;
        }
        return response.json();
    })
    .then(responseJson => {
        responseJson.forEach(function(option) {
            searchDatalist.append(`<option value="${option}">`);
        });
        errorDiv.innerHTML = "";
        errorDiv.removeAttribute("class")
    })
    .catch(err => {
        $('#errorDiv').addClass('alert alert-danger');
        errorDiv.innerHTML = err.message;
    });
});
