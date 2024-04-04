// wait animation with wait-modal
$body = $("body");
$(document).on({
    ajaxStart: function() { $body.addClass("loading");    },
     ajaxStop: function() { $body.removeClass("loading"); }
});


function submitForm(){
    // Save form data to sessionStorage on form submission
    // Get form data
    let form = document.getElementById("createVSForm");
    if (form.checkValidity()) {
        const formData = {
            vsLoadBalancerSelect: document.getElementById("vsLoadBalancerSelect").value,
            vsName: document.getElementById("vsName").value,
            vServerConfigSelect: document.getElementById("vServerConfigSelect").value,
            vsPort: document.getElementById("vsPort").value,
            searchContent: document.getElementById("searchContent").value,
            redirectHttpsCheck: document.getElementById("redirectHttpsCheck").value,
            redirectHttpsChecked: document.getElementById("redirectHttpsCheck").checked,
            vsIpAddr: document.getElementById("vsIpAddr").value,
            wafSvcIpAddr: document.getElementById("wafSvcIpAddr").value,
            wafRetIpAddr: document.getElementById("wafRetIpAddr").value,
            serviceProtoSelect: document.getElementById("serviceProtoSelect").value,
            serviceCountSlide: document.getElementById("serviceCountSlide").value,
            servIp: [],
            servPort: [],
            persistenceSelect: document.getElementById("persistenceSelect").value,
            lbMethodSelect: document.getElementById("lbMethodSelect").value,
            adUser: document.getElementById("adUser").value
        };
        // Get all input values
        const serviceBlocks = document.querySelectorAll('[id^="serviceBlock"]');
        serviceBlocks.forEach(function(block) {
            const servIpInput = block.querySelector('input[name="serv_ip[]"]');
            const servPortInput = block.querySelector('input[name="serv_port[]"]');
            formData.servIp.push(servIpInput.value);
            formData.servPort.push(servPortInput.value);
            });

        // Save form data to sessionStorage
        sessionStorage.setItem("formData", JSON.stringify(formData));
        form.submit();
        $(".loading-icon").removeClass("visually-hidden");
        $("#createVSForm").attr("disabled", true);
        $("#createVSBtn").attr("disabled", true);
        $("#btnText").text("Submitting ...");
    } else {
        form.reportValidity();
    }
}

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

    // Input Preserve Code block Begin
    // Check if sessionStorage has form data and populate the form fields
    if (sessionStorage.getItem("formData")) {
        const formData = JSON.parse(sessionStorage.getItem("formData"));
        document.getElementById("vsLoadBalancerSelect").value = formData.vsLoadBalancerSelect;
        document.getElementById("vsName").value = formData.vsName;
        document.getElementById("vServerConfigSelect").value = formData.vServerConfigSelect;
        document.getElementById("vsPort").value = formData.vsPort;
        document.getElementById("searchContent").value = formData.searchContent;
        document.getElementById("redirectHttpsCheck").value = formData.redirectHttpsCheck;
        document.getElementById("redirectHttpsCheck").checked = formData.redirectHttpsChecked;
        document.getElementById("vsIpAddr").value = formData.vsIpAddr;
        document.getElementById("wafSvcIpAddr").value = formData.wafSvcIpAddr;
        document.getElementById("wafRetIpAddr").value = formData.wafRetIpAddr;
        document.getElementById("serviceProtoSelect").value = formData.serviceProtoSelect;
        document.getElementById("serviceCountSlide").value = formData.serviceCountSlide;
        document.getElementById("serviceCountDisplay").innerHTML = formData.serviceCountSlide;  
        document.getElementById("persistenceSelect").value = formData.persistenceSelect;
        document.getElementById("lbMethodSelect").value = formData.lbMethodSelect;
        document.getElementById("adUser").value = formData.adUser;
        const serviceBlocks = document.querySelectorAll('[id^="serviceBlock"]');
        // Populate the form fields with stored data
        serviceBlocks.forEach(function(block, index) {
            const servIpInput = block.querySelector('input[name="serv_ip[]"]');
            const servPortInput = block.querySelector('input[name="serv_port[]"]');
            if (formData.servIp && formData.servIp[index]) {
                servIpInput.value = formData.servIp[index];
            }
            if (formData.servPort && formData.servPort[index]) {
                servPortInput.value = formData.servPort[index];
            }
        });
        // Input Preserve Code block End
        //
        // show hide controls Begin
        if (formData.vServerConfigSelect == "ssl") { 

            $('#sslProfileDiv').show();
            $('#redirectHttpsCheckDiv').show();
            $('#wafSvcIpDiv').hide();
            $('#wafRetIpDiv').hide();

        } else if (formData.vServerConfigSelect == "waf") { 

            $('#sslProfileDiv').show();
            $('#redirectHttpsCheckDiv').show();
            $('#wafSvcIpDiv').show();
            $('#wafRetIpDiv').show();

        } else if (formData.vServerConfigSelect == "http" || answer == "tcp") {
            $('#sslProfileDiv').hide();
            $('#redirectHttpsCheckDiv').hide();
            $('#wafSvcIpDiv').hide();
            $('#wafRetIpDiv').hide();
        }

        document.getElementById('serviceBlock1').style.display = "none";
        document.getElementById('serviceBlock2').style.display = "none";
        document.getElementById('serviceBlock3').style.display = "none";
        document.getElementById('serviceBlock4').style.display = "none";
        document.getElementById('serviceBlock5').style.display = "none";

        if (formData.serviceCountSlide == 1) { // hide the div that is not selected

          document.getElementById('serviceBlock1').style.display = "block";

        } else if (formData.serviceCountSlide == 2) { // hide the div that is not selected

          document.getElementById('serviceBlock1').style.display = "block";
          document.getElementById('serviceBlock2').style.display = "block";

        } else if (formData.serviceCountSlide == 3) { // hide the div that is not selected

          document.getElementById('serviceBlock1').style.display = "block";
          document.getElementById('serviceBlock2').style.display = "block";
          document.getElementById('serviceBlock3').style.display = "block";

        } else if (formData.serviceCountSlide == 4) { // hide the div that is not selected

          document.getElementById('serviceBlock1').style.display = "block";
          document.getElementById('serviceBlock2').style.display = "block";
          document.getElementById('serviceBlock3').style.display = "block";
          document.getElementById('serviceBlock4').style.display = "block";

        } else if (formData.serviceCountSlide == 5) { // hide the div that is not selected

          document.getElementById('serviceBlock1').style.display = "block";
          document.getElementById('serviceBlock2').style.display = "block";
          document.getElementById('serviceBlock3').style.display = "block";
          document.getElementById('serviceBlock4').style.display = "block";
          document.getElementById('serviceBlock5').style.display = "block";

        }
    }
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

// prevent form inputs to be get lost
document.addEventListener("DOMContentLoaded", function() {

  });
