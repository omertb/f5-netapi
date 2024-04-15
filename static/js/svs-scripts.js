
// wait animation with wait-modal
$body = $("body");
$(document).on({
    ajaxStart: function() { $body.addClass("loading");    },
     ajaxStop: function() { $body.removeClass("loading"); }
});

let $vServersTable = $('#vServersTable');

document.addEventListener("DOMContentLoaded", function() { 
    $.ajax({
        type: "GET",
        url: "/vs/virtuals.json",
        success: function(data) {
            $vServersTable.bootstrapTable("destroy");
            $vServersTable.bootstrapTable({data: data});
            errorDiv.innerHTML = "";
            errorDiv.removeAttribute("class")
        },
        error: function(data) {
            $vServersTable.bootstrapTable("destroy");
            $('#errorDiv').addClass('alert alert-danger');
            errorDiv.innerHTML = data.responseJSON.message;
        }
    });

    // Initialize tooltips on the table
    var table = document.getElementById('vServersTable');
    
    var tooltip = new bootstrap.Tooltip(table, {
        container: 'body',
        selector: '.tooltip-trigger'
    });
    /*
    var popover = new bootstrap.Popover(table, {
        container: 'body',
        selector: '.popover-trigger',
        trigger: 'hover'
    });
    */
});