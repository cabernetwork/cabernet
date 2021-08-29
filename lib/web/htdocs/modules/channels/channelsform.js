$(document).ready(setTimeout(function(){
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
        $('div[id$=-menu]').each(function() {
            $(this).hide();
        });

        if ( $('input[name=sort_dir]').val() ) {
            $.ajax({
                data: $(this).serialize(),
                type: $(this).attr('method'), // GET or POST
                url: $(this).attr('action'),
                success: function(response) { // on success
                    $('#tablecontent').html(response);
                }
            });
        } else {
            $.ajax({
                data: $(this).serialize(),
                type: $(this).attr('method'), // GET or POST
                url: $(this).attr('action'),
                success: function(response) { // on success
                    $('#status').html(response);
                }
            });
        }
        return false; // cancel original submit event
    });

    $('div#enabled-menu input').each(function() {
        $(this).click(function() {
            cbEnabledCheckboxClicked($(this));
        });
    });

    $("div[id$=-menu] input[type=text]").each(function() {
        var id = $(this).parent().parent().parent().prop('id');
        var name = id.replace('-menu', '');
        $(this).on('input', function() {
            var $this = $(this);
            keyDelay(function() {
                cbTextfilterTextKeyInput($this, name, id)
            }, 1200 );
        });
    });
    var keyDelay = (function() {
        var timer = 0;
        return function(callback, ms) {
            clearTimeout(timer);
            timer = setTimeout(callback, ms);
        };
    })();
    
    $('div[id$=-menu] input[id=text-mi][type=checkbox]').each(function() {
        var id = $(this).parent().parent().parent().prop('id');
        var name = id.replace('-menu', '');
        $(this).click(function() {
            cbTextfilterCheckboxClicked($(this), id, name);
        });
    });

    var cbEnabledCheckboxClicked = function(elemClicked) {
        if ( elemClicked.is(':checked') ) {
            c = true;
        } else {
            c = false;
        }
        filterText = elemClicked.prop('id').replace('-mi','');
        $('td.'+filterText).each(function() {
            if ( c ) {
                $(this).parent().removeClass(filterText+"-hide");
            } else {
                $(this).parent().addClass(filterText+"-hide");
            }
        });
        if ( $('div#enabled-menu input:checkbox:not(:checked)').length > 0 ) {
            $('table.sortable th:nth-child(1)').css({"background": "rgba(155,255,155,0.3)"});
        } else {
            $('table.sortable th:nth-child(1)').css({"background": ""});
        }
    }

    var cbTextfilterCheckboxClicked = function(elemClicked, id, name) {
        $("table.sortable th label:contains('"+name+"')").each(function() {
            index = $(this).parent().index()+1;
        });
        if ( !elemClicked.is(':checked') ) {
            $('div[id='+id+'] input[type=text]').val('');
            $('table.sortable th:nth-child('+index+')').css({"font-style": "inherit", "background": ""});
            $('table.sortable td:nth-child('+index+')').each(function() {
                $(this).parent().removeClass(name+"-hide");
            });
        }
    }

    var cbTextfilterTextKeyInput = function(elemClicked, name, id) {
        var keyValue = elemClicked.val();
        var index;
        $("table.sortable th label:contains('"+name+"')").each(function() {
            index = $(this).parent().index()+1;
        });
        if ( keyValue == "" ) {
            $('div[id='+id+'] input[type=checkbox]').prop('checked', false);
            $('table.sortable td:nth-child('+index+')').each(function() {
                $(this).parent().removeClass(name+"-hide");
            });
            $('table.sortable th:nth-child('+index+')').css({"font-style": "inherit", "background": ""});
        } else {
            $('div[id='+id+'] input[type=checkbox]').prop('checked', true);
            $('table.sortable td:nth-child('+index+')').each(function() {
                if ( $(this).find('input').length > 0 ) {
                    if ( $(this).find('input').val().toLowerCase().includes(keyValue.toLowerCase()) ) {
                        $(this).parent().removeClass(name+"-hide");
                    } else {
                        $(this).parent().addClass(name+"-hide");
                    }
                } else {
                    if ( $(this).text().toLowerCase().includes(keyValue.toLowerCase()) ) {
                        $(this).parent().removeClass(name+"-hide");
                    } else {
                        $(this).parent().addClass(name+"-hide");
                    }
                }
            });
            $('table.sortable th:nth-child('+index+')').css(
                {"font-style": "italic", "background": "rgba(155,255,155,0.3)"});
        }
    }

    var resetFilters = function(arg1) {
        $('div.xmenu input[type=checkbox]').each(function() {
            var id = $(this).parent().parent().parent().prop('id');
            var name = id.replace('-menu', '');
            inputName = $(this).attr('name');
            ckbxStatus = $(this).is(':checked');
            if ( inputName.endsWith('-mi') ) {
                if (!ckbxStatus) {
                    cbEnabledCheckboxClicked($(this));
                }
            } else {
                if (ckbxStatus) {
                    cbTextfilterTextKeyInput($(this).parent().find('input[type=text]'), name, id);
                }
            }
        });
    }
    resetFilters();
    
}, 100));
