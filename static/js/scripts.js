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


    // spinner for form submit
    $(document).ready(function() {
        $("#createVSBtn").click(function() {
            // disable button
            $(this).prop("disabled", true);
            // add spinner to button
            $(this).html(
                `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...`
            );
            $("#createVSForm").submit();
        });

    // Check if the table has any rows
    if ($('tbody tr').length == 0) {
        // Hide the table header and toolbar content
        $('thead').hide();
    }
    const searchInput = $("#searchContent");
    const searchDatalist = $("#searchDatalistOptions");
    let errorDiv = document.getElementById("errorDiv");

    //searchInput.on("keyup", delay(function() {
    searchInput.one("focus", delay(function() {
        //if (searchInput.val().length == 3) {
            // clear previous options
            searchDatalist.empty();
            fetch("/cert/sslprofiles.json", {
                method: "GET",
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
    }, 250));
});