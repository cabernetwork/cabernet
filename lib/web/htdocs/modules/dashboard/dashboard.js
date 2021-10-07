$(document).ready(setTimeout(function(){

    function populateDashboard(tuner_data, schedule_data) {
        populateTuner(tuner_data);
        populateSchedule(schedule_data);
    }

    function populateTuner(tuner_data) {
        $('#dashboard').append('<h3 style="margin:0;">Tuner Status</h3><table id="tuners" ></table>');
        $('#tuners').append('<thead><tr><th class="header" style="min-width: 10ch;">State</th>'
            + '<th class="header" style="min-width: 10ch;">Plugin</th>'
            + '<th class="header" style="min-width: 10ch;">Tuner</th>'
            + '<th class="header" style="min-width: 10ch;">Instance</th>'
            + '<th class="header" style="min-width: 10ch;">Channel</th></thead>'
            );
        $.each(tuner_data, function(key1, list_value) {
            if(list_value !== null) {
                if (typeof list_value === 'object' ) {
                    $.each(list_value, function(key2, tuner_status) {
                        if (typeof tuner_status === 'object' ) {
                            $('#tuners').append('<tr><td>Active</td><td>' + key1 + '</td><td>tuner' + key2 + '</td><td>' + tuner_status.instance + '</td><td>' + tuner_status.ch + '</td></tr>');
                        }
                    });
                }
            }
        });
    }

    function populateSchedule(sched_data) {
        $('#dashboard').append('<br><h3 style="margin:0;">Scheduler Status</h3><table id="sched" ></table>');
        $('#sched').append('<thead><tr><th class="header" style="min-width: 10ch;">State</th>'
            + '<th class="header" style="min-width: 10ch;">Area</th>'
            + '<th class="header" style="min-width: 10ch;">Title</th>'
            + '<th class="header" style="min-width: 10ch;">Plugin</th>'
            + '<th class="header" style="min-width: 10ch;">Instance</th></thead>'
            );
        $.each(sched_data, function(key1, dict_value) {
            console.log(key1, dict_value)
            if(dict_value !== null) {
                $('#sched').append('<tr><td>Running</td><td>' + dict_value.area + '</td><td>' + dict_value.title + '</td><td>' + dict_value.namespace + '</td><td>' + dict_value.instance + '</td></tr>');
            }
        });
    }

    populateDashboard(tunerstatus, schedstatus)
}, 1000));
