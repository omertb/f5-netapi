// wait animation with wait-modal
$body = $("body");
$(document).on({
    ajaxStart: function() { $body.addClass("loading");    },
     ajaxStop: function() { $body.removeClass("loading"); }
});


// disable button when submittin on create vs form
$(document).ready(function() {
    $("#createVSForm").submit(function(event) {
        
        $(".loading-icon").removeClass("visually-hidden");
        $("#createVSForm").attr("disabled", true);
        $("#createVSBtn").attr("disabled", true);
        $("#btnText").text("Submitting ...");
        
       /*
        // if the form is invalid, let the browser handle validation
        if (this.checkValidity()) {
            return false;
        }
        event.preventDefault();
        let formData = $(this).serialize();
        $.ajaxSetup({
            headers: {
                "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
            }
        });
        $.ajax({
            type: "POST",
            url: "/vs",
            data: formData,
            success: function(response_data){
                document.getElementById("successDivList").innerHTML = '<li>' + response_data.join('</li><li>') + '</li>';
            },
            error: function(response_data){
                document.getElementById("errorDivList").innerHTML = '<li>' + response_data.join('</li><li>') + '</li>';
            }
        });
        */
        
    });
});

const searchInput = $("#searchContent");
const searchDatalist = $("#searchDatalistOptions");
let errorDiv = document.getElementById("errorDiv");
let loadBalancerSelect = document.getElementById("vsLoadBalancerSelect");
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
