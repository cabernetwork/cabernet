$(document).ready(function(){
    $('form').submit(function() { // catch the form's submit
        $(this).find('input[type="checkbox"]').each(function() {
            if ($(this).is(":checked") == true) {
                var n = '#'+$(this).attr("id")+'hidden';
                $(n).prop("disabled", true);
            } else {
                var n = '#'+$(this).attr("id")+'hidden';
                $(n).prop("disabled", false);
            }
        });
        $.ajax({
            data: $(this).serialize(),
            type: $(this).attr('method'), // GET or POST
            url: $(this).attr('action'),
            success: function(response) { // on success
                $('#reset_status').html(response);
            }
        });
        return false; // cancel original submit event
    });
});

function load_dm_url(url) {
    $("#content").load(url);
    return false;
}
function load_backup_url(url) {
    $("#dmbackup").load(url);
    return false;
}
function display_tasks() {
    $('div#schedtasks').each(function() {
        $(this).removeClass("schedHide");
        $(this).addClass("schedShow");
    });
    $('div#schedtask').each(function() {
        $(this).removeClass("schedShow");
        $(this).addClass("schedHide");
    });
}
function onChangeTimeType(timetype) {
    if (timetype.value == 'weekly') {
        $('#divDOW').each(function() {
            $(this).removeClass("schedHide");
            $(this).addClass("schedShow");
        });
        $('#divTOD').each(function() {
            $(this).removeClass("schedHide");
            $(this).addClass("schedShow");
        });
        $('#divINTL').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divRND').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
    } else if (timetype.value == 'daily') {
        $('#divDOW').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divTOD').each(function() {
            $(this).removeClass("schedHide");
            $(this).addClass("schedShow");
        });
        $('#divINTL').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divRND').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
    } else if (timetype.value == 'interval') {
        $('#divINTL').each(function() {
            $(this).removeClass("schedHide");
            $(this).addClass("schedShow");
        });
        $('#divRND').each(function() {
            $(this).removeClass("schedHide");
            $(this).addClass("schedShow");
        });
        $('#divDOW').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divTOD').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
    } else if (timetype.value == 'startup') {
        $('#divINTL').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divRND').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divDOW').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
        $('#divTOD').each(function() {
            $(this).removeClass("schedShow");
            $(this).addClass("schedHide");
        });
    }

}

