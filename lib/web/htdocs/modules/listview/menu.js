$(document).ready(function(){
});

function show_menu(_button, _menuid) {
    switch_display(_button, _menuid);
    reset_menu_posn(_button, _menuid);
    return false;
}

function reset_menu_posn(_el_button, _menuid) {
    menuid = '#' + _menuid;

    var _el_menu_rect = $(menuid)[0].getBoundingClientRect();
    var _el_button_rect = _el_button.getBoundingClientRect();
    var _el_menu_height = _el_menu_rect.height;
    var _el_button_height = _el_button_rect.height;
    var _el_button_left = _el_button.scrollLeft;

    if ( _el_button_rect.y + _el_button_height < _el_button_height ) {
        _top = _el_button.offsetTop - _el_button_rect.y;
    } else {
        _top = _el_button.offsetTop - _el_menu_height + _el_button_height;
    }
    var _el_button_width = _el_button_rect.width;
    var _el_menu_width = _el_menu_rect.width;

    var panel_width = _el_button.parentElement.getBoundingClientRect().width;
    if ( panel_width - _el_button_width - 5 < _el_menu_width ) {
        _left = _el_button_left + _el_button_width/2;
    } else {
        _left = _el_button_left + _el_button_width;
    }
    $(menuid).css({"top":_top+'px', "left":_left+'px'});

    var _el_menu_rect = $(menuid)[0].getBoundingClientRect();
    var _el_menu_height = _el_menu_rect.height;
    if ( _el_button_rect.y + _el_button_height < _el_menu_height ) {
        _top = _el_button.offsetTop - _el_button_rect.y;
    } else {
        _top = _el_button.offsetTop - _el_menu_height + _el_button_height;
    }
    $(menuid).css({"top":_top+'px', "left":_left+'px'});
}

function switch_display(_button, _menuid) {
    $('div#'+_menuid).each(function() {
        if ( $(this).hasClass("listItemHide") ) {
            $(this).removeClass("listItemHide");
            $(this).addClass("listItemShow");
            $(this).focus().select();
            $(document).on('click', function(e) {
                var _menu = $('#'+_menuid);
                var _button2 = $('.menuSection');
                if ( !$(e.target).closest(_menu).length ) {
                    if ( !$(e.target).closest(_button2).length ) {
                        switch_display(_button, _menuid);
                    }
                }
            });
            $('#menuForm').submit(function(e) { // catch the form's submit
                // ajax does not submit name/value of button, so use hidden input
                $('input:hidden[name=action]').val(e.originalEvent.submitter.value);
                $.ajax({
                    data: $(this).serialize(),
                    type: $(this).attr('method'), // GET or POST
                    url: $(this).attr('action'),
                    success: function(response) { // on success
                        $('#menuActionStatus').html(response);
                    }
                });
                return false; // cancel original submit event
            });
            
        } else {
            $(this).removeClass("listItemShow");
            $(this).addClass("listItemHide");
            $(document).prop('onclick', null).off("click"); 
            $('#menuForm').prop("onsubmit", null).off("submit");
        }
    });
    
}

