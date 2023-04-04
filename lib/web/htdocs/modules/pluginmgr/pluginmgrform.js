$(document).ready(setTimeout(function(){
    $('form').submit(function(e) { // catch the form's submit
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
    
}, 500));
