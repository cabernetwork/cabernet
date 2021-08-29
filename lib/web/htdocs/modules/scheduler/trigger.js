$(document).ready(setTimeout(function(){
    $('form').submit(function() {
        $.ajax({
            data: $(this).serialize(),
            type: $(this).attr('method'), // GET or POST
            url: $(this).attr('action'),
            success: function(response) { // on success
                $('#status').html(response);
            }
        });
        return false;
    });
}, 100));