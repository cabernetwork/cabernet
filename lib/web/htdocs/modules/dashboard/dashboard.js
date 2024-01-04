$(document).ready(setTimeout(function(){
    var tunerstatus = {}
    var schedstatus = []
    var expire = 0

    function getDashboardStatus(){
        return $.getJSON("/api/dashstatus.json").then(function(json){
            return json;
        });
    }

    function populateDashboard() {
        getDashboardStatus().then(function(json_dashboard) {
            tunerstatus = json_dashboard['tunerstatus']
            schedstatus = json_dashboard['schedstatus']
            tuner_active = populateTuner(tunerstatus);
            sched_active = populateSchedule(schedstatus);
            if ( tuner_active || sched_active ) {
                expire = 1000;
            } else if (expire < 30000) {
                expire = expire + 3000;
            }
            setTimeout(function(){
                if($("#dashboard").length !== 0) {
                    populateDashboard();
                }
            }, expire);
        });
    }

    function populateTuner(tuner_data) {
        $('#dashboard').html('<h3 style="margin:0;">Tuner Status</h3><table id="tuners" ></table>');
        $('#tuners').append('<thead><tr><th class="header" style="min-width: 10ch;">State</th>'
            + '<th class="header" style="min-width: 10ch;">Plugin</th>'
            + '<th class="header" style="min-width: 7ch;">Tuner</th>'
            + '<th class="header" style="min-width: 10ch;">Instance</th>'
            + '<th class="header" style="min-width: 7ch;">Channel</th>'
            + '<th class="header" style="min-width: 7ch;">Clients</th></thead>'
            );
        var active = false;
        if ( tuner_data === null ) {
            $('#tuners').append('<tr><td colspan=5>Tuner Status is Down, check 5004 process</td></tr>');
        } else {
            $.each(tuner_data, function(key1, list_value) {
                if(list_value !== null) {
                    if (typeof list_value === 'object' ) {
                        $.each(list_value, function(key2, tuner_status) {
                            if (typeof tuner_status === 'object' ) {
                                $('#tuners').append('<tr><td>' + tuner_status.status +'</td><td>' + key1 + '</td><td>tuner' + key2 + '</td><td>' + tuner_status.instance + '</td><td>' + tuner_status.ch + '</td><td>' + tuner_status.mux + '</td></tr>');
                                active = true;
                                console.log(tuner_status);
                            }
                        });
                    }
                }
            });
        }
        return active;
    }

    function populateSchedule(sched_data) {
        $('#dashboard').append('<br><h3 style="margin:0;">Scheduler Status</h3><table id="sched" ></table>');
        $('#sched').append('<thead><tr><th class="header" style="min-width: 10ch;">State</th>'
            + '<th class="header" style="min-width: 10ch;">Area</th>'
            + '<th class="header" style="min-width: 10ch;">Title</th>'
            + '<th class="header" style="min-width: 10ch;">Plugin</th>'
            + '<th class="header" style="min-width: 10ch;">Instance</th></thead>'
            );
        var active = false;
        $.each(sched_data, function(key1, dict_value) {
            if(dict_value !== null) {
                $('#sched').append('<tr><td>Running</td><td>' + dict_value.area + '</td><td>' + dict_value.title + '</td><td>' + dict_value.namespace + '</td><td>' + dict_value.instance + '</td></tr>');
                active = true
            }
        });
        return active;
    }
    populateDashboard();
}, 1000));
