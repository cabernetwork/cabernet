function load_form_url(url) {
    $("#pluginscontent").load(url);
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
