$(document).ready(function(){
    $('form select[class=dlevelsetting]').change(function() {
        setDisplayLevel();
    });

    var getConfigData = function(){
        $.getJSON("/config.json", function(json) {
            if (json != "Nothing found."){
                var currentDisplayLevel = $('form select[class=dlevelsetting]').val();
                if (typeof currentLevelValue === 'undefined') {
                    currentDisplayLevel = json.display.display_level;
                    $("form select[class=dlevelsetting]").val(currentDisplayLevel);
                }
                $('.sectionForm').each(function(){
                    populateForm("#"+$(this).attr("id"), json, null)
                    setDisplayLevel("#"+$(this).attr("id"))
                })
            } else {
                $('#status').html('<h2 class="loading">Were afraid nothing was returned. is the web interface disabled?</h2>');
            }
            return true;
        })
        .fail(function() {
                $('#status').html('<h2 class="loading">Unable to obtain config data. Is the config web interface disabled?</h2>');
                $('button#submit').prop("disabled",true);
                return false;
        })
        return false;
    }

    function populateForm(form,data,parent) {
        $.each(data, function(key, value) {
            if(value !== null) {
                if (typeof value === 'object' ) {
                    populateForm(form,value,key+'-')
                } else {
                    if (parent === null) {
                        var ctrl = $('[name='+key+']', form);
                    } else {
                        var ctrl = $('[name='+parent+key+']', form);
                    }
                    switch(ctrl.prop("type")) {
                        case "radio": case "checkbox":
                            ctrl.each(function() {
                                if ($(this).attr('value') == value) $(this).attr("checked",value);
                                $(this).prop("checked",value);
                            });
                            break;
                        case undefined:
                            break;
                        case "text": case "hidden": case "password":
                            ctrl.val(value);
                            vallength = value.length+5
                            if (vallength < 15) {
                                vallength = 15
                            }
                            ctrl.attr('size', vallength)
                            break;
                        default:
                            ctrl.val(value);
                    }
                }
            }
        });
    }

    function getDisplayLevel() {
        var currentDisplayLevel = $('form select[class=dlevelsetting]').val();
        if (typeof currentLevelValue === 'undefined') {
            currentDisplayLevel = $('select[class=dlevelsetting]').val();
        }
        if (currentDisplayLevel == '') {
            currentDisplayLevel = '1-Standard'
        }
        return currentDisplayLevel;
    }
    x=1
    function setDisplayLevel() {
        x+=1
        var currentDisplayLevel = getDisplayLevel();
        var currentLevel = currentDisplayLevel.match(/^\d+/)[0];
        $('form tr[class^="dlevel"]').each(
            function(index) {
                var input = $(this)
                var itemLevel = input.attr('class').match(/\d+$/)[0];
                if (itemLevel > currentLevel) {
                    $(this).hide()
                } else {
                    $(this).show()
                }
        });
        $('form tr[class="hlevel"]').each(
            function() {
                allHidden = true;
                $(this).nextUntil('tr[class="hlevel"]').each(
                    function() {
                        if ( $(this).css("display") != "none" ) {
                            allHidden = false;
                        }
                    }
                )
                if (allHidden) {
                    $(this).hide()
                } else {
                    $(this).show()
                }
        });
        $('a.configTab').hide();
        $('form[class="sectionForm"]').each(
            function() {
                formname = $(this).attr("id");
                $(this).find('tr[class^="dlevel"]').each(
                    function(i) {
                        if ( this.style.display !== "none" ) {
                            // at least one is active.  turn on tab
                            $('a.'+formname).show();
                        }
                    }
                )
            });
    }
    getConfigData();
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
                $('#status').html(response);
            }
        });
        return false; // cancel original submit event
    });
});
