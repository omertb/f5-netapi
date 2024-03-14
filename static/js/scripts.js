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

    
$(document).ready(function() {
    // Check if the table has any rows
    if ($('tbody tr').length == 0) {
        // Hide the table header and toolbar content
        $('thead').hide();
    }
});
