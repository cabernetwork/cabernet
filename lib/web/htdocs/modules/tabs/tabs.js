$(document).ready(function() {
    $('.configTab').each(function() {
        $(this).click(function() {
            $('a.configTab').removeClass("activeTab");
            $(this).addClass("activeTab");
            $('form.sectionForm').hide();
            var section = $(this).attr("id").substring(3);
            $("#form"+section).show();
            event.preventDefault();
        });
    });
    $('form.sectionForm').hide();
    var activeTab = $("a.activeTab").attr("id").substring(3);
    $('#form'+activeTab).each(function() {
        $(this).show();
    });

});