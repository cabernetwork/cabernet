$(document).ready(function() {
    $('.navOpenPanel').css("z-index","1");
    $('.navOpenPanel').on("click", function() {
        $('div.mainDrawer').show(500);
        $('div.skinBody-withFullDrawer').css("left", "");
        $('button.navOpenPanel').hide();
    });
    $('button.navClosePanel').each(function() {
        $(this).click(function() {
            $('div.mainDrawer').hide(500);
            $('div.skinBody-withFullDrawer').css({"left": "0em", "transition": "left .5s"});
            $('button.navOpenPanel').show();
        });
    });
    $('button.navOpenPanel').hide();
    $('a.navMenuOption').on("click", function() {
        $('a.navMenuOption').removeClass('navMenuOption-selected');
        $(this).addClass('navMenuOption-selected');        
    });
    
    
    
});