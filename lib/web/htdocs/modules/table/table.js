$(document).ready(setTimeout(function() {
    $('table.sortable th img.sortit').each(function() {
        
        $(this).click(function() {
            if ( $(this).hasClass("sortnone") ) {
                newDirection = 'sortasc';
            } else if ( $(this).hasClass("sortasc") ) {
                newDirection = 'sortdesc';
            } else if ( $(this).hasClass("sortdesc") ) {
                newDirection = 'sortnone';
            } else {
                newDirection = 'sortasc';
            }
            var text = getCellText($(this));
            $('input[name=sort_col]').val(text)
            $('input[name=sort_dir]').val(newDirection)
            $('form:first').submit()
            $('input[name=sort_col]').val(null)
            $('input[name=sort_dir]').val(null)
        });
    });
    
    $('table.sortable th img.filterit').each(function() {
        $(this).click(function() {
            var text = getCellText($(this));
            var outerWidth = 0;
            var innerWidth = 0;
            var popupElem;
            var isVisible = $('div#'+text+'-menu').is(':visible');
            $('div[id$=-menu]').each(function() {
                $(this).hide();
            });
            $('div#'+text+'-menu').each(function() {
                if ( !isVisible ) {
                    $(this).show();
                }
                outerWidth = $(this).outerWidth();
                innerWidth = $(this).innerWidth();
                popupElem = $(this);
            });
            var $left = $(this).offset().left - $('table.sortable').offset().left - $('#tablecontent').scrollLeft();
            var $farleft = $('table.sortable').width() - outerWidth -2 - $('#tablecontent').scrollLeft();
            var $width = innerWidth;
            if ($left > $farleft) {
                $left = $farleft;
            }
            var $bottom = $(this).offset().top + $(this).outerHeight() + 1 +$('.scrollFrameY').scrollTop();
            popupElem.css({
                left: $left,
                top: $bottom,
                width: $width,
            });
        });
    });
    
    $('table.sortable th input[type=checkbox]').each(function() {
        $(this).change(function() {
            var id = $(this).attr('id');
            var checked = $(this).is(':checked');
            $('table.sortable tr:not([class$="-hide"]) td input.'+id+':checkbox').each(function() {
                $(this).prop('checked', checked);
            });
        });
    });
    
    function getCellText(elem) {
        text = elem.parent().text();
        if (!text) {
            text = elem.parent().parent().find("input").attr("id");
        }
        return text
    }

}, 1000));
