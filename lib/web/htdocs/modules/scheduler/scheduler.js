$(document).ready(function() {
    if (timeout != undefined) {
        clearTimeout(timeout);
        timeout = null;
    }
    $('div.progress-line:first').each(function() {
        reload_div();
    });

});
var timeout;
function reload_div(){
    timeout = setTimeout(function(){
        display_status = $("#schedtasks").css('display');
        if (display_status == 'none') {
            reload_div();
        }
        else if (display_status == 'block') {
            load_sched_url('/api/schedulehtml');
        }
    }, 5000);
}
function load_task_url(url) {
    $('div#schedtasks').each(function() {
        $(this).removeClass("schedShow");
        $(this).addClass("schedHide");
    });
    $('div#schedtask').each(function() {
        $(this).removeClass("schedHide");
        $(this).addClass("schedShow");
    });
    $("#schedtask").load(url);
    return false;
}

function load_sched_url(url) {
    $("#content").load(url);
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

