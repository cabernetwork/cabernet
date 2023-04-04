function load_form_url(url) {
    $("#pluginscontent").load(url);
    $('div#pluginscontent').each(function() {
        $(this).removeClass("pluginHide");
        $(this).addClass("pluginShow");
    });
    $('div#plugincontent').each(function() {
        $(this).removeClass("pluginShow");
        $(this).addClass("pluginHide");
    });    
    return false;
}

function load_plugin_url(url) {
    $("#plugincontent").load(url);
    $('div#pluginscontent').each(function() {
        $(this).removeClass("pluginShow");
        $(this).addClass("pluginHide");
    });
    $('div#plugincontent').each(function() {
        $(this).removeClass("pluginHide");
        $(this).addClass("pluginShow");
    });
    
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

    
    
    
    
    return false;
}

function display_plugins() {
    $('div#pluginscontent').each(function() {
        $(this).removeClass("pluginHide");
        $(this).addClass("pluginShow");
    });
    $('div#plugincontent').each(function() {
        $(this).removeClass("pluginShow");
        $(this).addClass("pluginHide");
    });
    return false;
}
