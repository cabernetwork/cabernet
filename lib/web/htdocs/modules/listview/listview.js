define(["itemContextMenu", "dom", "cardBuilder", "itemShortcuts", "itemHelper", "mediaInfo", "indicators", "connectionManager", "layoutManager", "globalize", "datetime", "apphost", "imageLoader", "focusManager", "css!./listview", "emby-ratingbutton", "emby-playstatebutton", "embyProgressBarStyle", "emby-linkbutton"], function(itemContextMenu, dom, cardBuilder, itemShortcuts, itemHelper, mediaInfo, indicators, connectionManager, layoutManager, globalize, datetime, appHost, imageLoader, focusManager) {
	"use strict";
	var supportsNativeLazyLoading = "loading" in HTMLImageElement.prototype;

	function getTextLinesHtml(textlines, isLargeStyle, allowTextWrap) {
		var html = "",
			isFirst = !0,
			cssClass = "listItemBodyText";
		allowTextWrap || (cssClass += " listItemBodyText-nowrap");
		for (var i = 0, length = textlines.length; i < length; i++) {
			var text = textlines[i];
			text && (html += isFirst ? isLargeStyle ? '<h3 class="' + cssClass + '">' : '<div class="' + cssClass + '">' : '<div class="' + cssClass + ' listItemBodyText-secondary">', html += text, html += isFirst && isLargeStyle ? "</h3>" : "</div>", isFirst = !1)
		}
		return html
	}

	function getId(item) {
		return item.Id
	}

	function getListItemHtml(item, index, options) {
		var enableOverview = options.enableOverview,
			enableSideMediaInfo = options.enableSideMediaInfo,
			clickEntireItem = options.clickEntireItem,
			isLargeStyle = options.isLargeStyle,
			enableContentWrapper = options.enableContentWrapper,
			tagName = options.tagName,
			action = options.action,
			html = "",
			downloadWidth = isLargeStyle ? 600 : 80;
		enableContentWrapper && (html += '<div class="listItem-content">');
		var imgUrl, imageContainerClass, imageClass, playOnImageClick, imageAction, color, icon, iconCssClass, indicatorsHtml, progressHtml, serverId = item.ServerId,
			apiClient = serverId ? connectionManager.getApiClient(serverId) : null,
			itemType = item.Type;
		!1 !== options.image && (imgUrl = cardBuilder.getImageUrl(item, apiClient, {
			width: downloadWidth,
			showChannelLogo: "channel" === options.imageSource
		}).imgUrl, imageContainerClass = "listItemImageContainer", imageClass = "listItemImage", isLargeStyle && (imageContainerClass += " listItemImageContainer-large", layoutManager.tv && (imageContainerClass += " listItemImageContainer-large-tv")), options.roundImage && (imageClass += " listItemImage-round", imgUrl || (imageContainerClass += " listItemImageContainer-round")), playOnImageClick = options.imagePlayButton && !layoutManager.tv, clickEntireItem || (imageContainerClass += " itemAction"), options.playlistItemId && options.playlistItemId === item.PlaylistItemId && (imageContainerClass += " playlistIndexIndicatorImage"), imageAction = playOnImageClick ? "resume" : action, imgUrl || options.transparentIcon || (imageContainerClass += " defaultCardBackground defaultCardBackground0"), html += '<div data-action="' + imageAction + '" class="' + imageContainerClass + '"' + ((color = "Error" === item.Severity || "Fatal" === item.Severity || "Warn" === item.Severity ? "background-color:#cc0000;color:#fff;" : "") ? ' style="' + color + '"' : "") + ">", imgUrl ? supportsNativeLazyLoading || 2 === options.lazy ? html += '<img class="' + imageClass + '" loading="lazy" src="' + imgUrl + '" />' : html += '<img class="' + imageClass + ' lazy" src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==" data-src="' + imgUrl + '" alt />' : !options.enableDefaultIcon || (icon = cardBuilder.getDefaultIcon(item)) && (iconCssClass = "listItemIcon md-icon", options.transparentIcon && (iconCssClass += " listItemIcon-transparent"), html += '<i class="' + iconCssClass + '">' + icon + "</i>"), (indicatorsHtml = indicators.getPlayedIndicatorHtml(item, "listItem")) && (html += '<div class="indicators listItemIndicators">' + indicatorsHtml + "</div>"), playOnImageClick && (html += '<button title="' + globalize.translate("Play") + '" type="button" is="paper-icon-button-light" class="listItemImageButton itemAction" data-action="resume"><i class="md-icon listItemImageButton-icon">&#xE037;</i></button>'), (progressHtml = indicators.getProgressBarHtml(item, {
			containerClass: "listItemProgressBar"
		})) && (html += progressHtml), html += "</div>"), options.showIndexNumberLeft && (html += '<div class="listItem-indexnumberleft secondaryText">', null == item.IndexNumber ? html += "&nbsp;" : html += item.IndexNumber, html += "</div>");
		var textlines = [];
		options.showProgramDateTime && textlines.push(datetime.toLocaleString(datetime.parseISO8601Date(item.StartDate), {
			weekday: "long",
			month: "short",
			day: "numeric",
			hour: "numeric",
			minute: "2-digit"
		})), options.showAccessToken && textlines.push(item.AccessToken + " - " + item.AppName), options.showProgramTime && textlines.push(datetime.getDisplayTime(datetime.parseISO8601Date(item.StartDate))), options.showChannel && item.ChannelName && textlines.push(dom.htmlEncode(item.ChannelName));
		var parentTitle = null;
		options.showParentTitle && ("Episode" === itemType ? parentTitle = item.SeriesName : (item.IsSeries || item.EpisodeTitle && item.Name) && (parentTitle = item.Name));
		var displayName = itemHelper.getDisplayName(item, {
			includeParentInfo: options.includeParentInfoInTitle
		});
		options.showIndexNumber && null != item.IndexNumber && (displayName = item.IndexNumber + ". " + displayName), options.showParentTitle && options.parentTitleWithTitle ? (displayName && (parentTitle && (parentTitle += " - "), parentTitle = (parentTitle || "") + displayName), textlines.push(dom.htmlEncode(parentTitle || ""))) : options.showParentTitle && textlines.push(dom.htmlEncode(parentTitle || "")), options.showLogLine && textlines.push(dom.htmlEncode(item)), displayName && !options.parentTitleWithTitle && textlines.push(dom.htmlEncode(displayName));
		var containerAlbumArtistIds, showArtist = !0 === options.artist,
			artistItems = "MusicAlbum" === item.Type ? item.AlbumArtists : item.ArtistItems;
		showArtist || !1 === options.artist || (containerAlbumArtistIds = options.containerAlbumArtistIds, artistItems && artistItems.length && !(1 < artistItems.length) && containerAlbumArtistIds && 1 === containerAlbumArtistIds.length && -1 !== containerAlbumArtistIds.indexOf(artistItems[0].Id) || (showArtist = !0)), showArtist && artistItems && textlines.push(artistItems.map(function(a) {
			return a.Type = "MusicArtist", a.IsFolder = !0,
				function(options, item, text, serverId, parentId, isSameItemAsCard) {
					if (text = text || itemHelper.getDisplayName(item), layoutManager.tv) return dom.htmlEncode(text);
					if (!1 === options.textLinks) return dom.htmlEncode(text);
					var html = '<button title="' + (text = dom.htmlEncode(text)) + '" ' + (isSameItemAsCard ? "" : itemShortcuts.getShortcutAttributesHtml(item, {
						serverId: serverId,
						parentId: parentId
					})) + ' type="button"' + (options.draggable && options.draggableSubItems && !isSameItemAsCard ? ' draggable="true"' : "") + ' class="itemAction textActionButton listItem-textActionButton" data-action="link">';
					return html += text, html += "</button>"
				}(options, a, null, item.ServerId)
		}).join(", ") || ""), "Game" === itemType ? textlines.push(dom.htmlEncode(item.GameSystem)) : "TvChannel" === itemType && item.CurrentProgram && textlines.push(dom.htmlEncode(itemHelper.getDisplayName(item.CurrentProgram))), options.showDateCreated && textlines.push(datetime.toLocaleString(datetime.parseISO8601Date(item.DateCreated, !0))), options.showDateModified && textlines.push(datetime.toLocaleString(datetime.parseISO8601Date(item.DateModified, !0))), options.showDate && textlines.push(datetime.toLocaleString(datetime.parseISO8601Date(item.Date, !0))), options.showShortOverview && textlines.push(item.ShortOverview ? dom.htmlEncode(item.ShortOverview) : "&nbsp;"), options.showMediaStreamInfo && mediaInfo.pushMediaStreamLines(item, options, textlines, cardBuilder.getDefaultIcon(item));
		var cssClass = "listItemBody";
		clickEntireItem || (cssClass += " itemAction"), !1 === options.image && (cssClass += " listItemBody-noleftpadding"), !1 === options.verticalPadding && (cssClass += " listItemBody-noverticalpadding"), options.code && (cssClass += " listItemBody-code"), html += "<" + options.listItemBodyTagName + ' class="' + cssClass + '">';
		var sideMediaInfo, userData, likes, userDataButtonsHtml;
		if (html += getTextLinesHtml(textlines, isLargeStyle, options.allowTextWrap), !1 !== options.mediaInfo && (enableSideMediaInfo || (html += '<div class="listItemMediaInfo listItemBodyText listItemBodyText-secondary listItemBodyText-nowrap">' + mediaInfo.getPrimaryMediaInfoHtml(item, {
				episodeTitle: !1,
				originalAirDate: !1,
				subtitles: !1,
				endsAt: !1
			}) + "</div>")), enableOverview && item.Overview && (html += '<div class="listItem-overview listItemBodyText listItemBodyText-secondary">', html += dom.htmlEncode(item.Overview), html += "</div>"), html += "</" + options.listItemBodyTagName + ">", !1 !== options.mediaInfo && (!enableSideMediaInfo || (sideMediaInfo = mediaInfo.getPrimaryMediaInfoHtml(item, {
				year: !1,
				container: !1,
				episodeTitle: !1,
				criticRating: !1,
				endsAt: !1
			})) && (html += '<div class="listItemMediaInfo secondaryText">' + sideMediaInfo + "</div>")), options.recordButton || "Timer" !== itemType && "Program" !== itemType || (html += indicators.getTimerIndicator(item).replace("indicatorIcon", "indicatorIcon listItemAside")), clickEntireItem || (options.addToListButton && (html += '<button title="' + globalize.translate("HeaderAddToPlaylist") + '" type="button" is="paper-icon-button-light" class="listItemButton itemAction" data-action="addtoplaylist"><i class="md-icon">&#xE03B;</i></button>'), options.openInNewWindowButton && appHost.supports("targetblank") && (html += '<a title="' + globalize.translate("HeaderOpenInNewWindow") + '" type="button" is="emby-linkbutton" href="' + apiClient.getLogDownloadUrl(item) + '" target="_blank" class="paper-icon-button-light listItemButton itemAction" data-action="default"><i class="md-icon">open_in_new</i></a>'), options.downloadButton && (html += '<button title="' + globalize.translate("Download") + '" type="button" is="paper-icon-button-light" class="listItemButton itemAction" data-action="download"><i class="md-icon">cloud_download</i></button>'), !1 !== options.moreButton && itemContextMenu.supportsContextMenu(item) && (html += '<button title="' + globalize.translate("More") + '" type="button" is="paper-icon-button-light" class="listItemButton listItemContextMenuButton itemAction" data-action="menu"><i class="md-icon">&#xE5D3;</i></button>'), options.infoButton && (html += '<button type="button" is="paper-icon-button-light" class="listItemButton itemAction" data-action="link"><i class="md-icon">&#xE88F;</i></button>'), options.deleteButton && (html += '<button title="' + globalize.translate("Delete") + '" type="button" is="paper-icon-button-light" class="listItemButton itemAction" data-action="delete"><i class="md-icon">delete</i></button>'), options.overviewButton && item.Overview && (html += '<button type="button" is="paper-icon-button-light" class="listItemButton itemAction" data-action="overview"><i class="md-icon">&#xE88F;</i></button>'), options.rightButtons && (html += function(options) {
				for (var html = "", i = 0, length = options.rightButtons.length; i < length; i++) {
					var button = options.rightButtons[i];
					html += '<button type="button" is="paper-icon-button-light" class="listItemButton itemAction" data-action="custom" data-customaction="' + button.id + '" title="' + button.title + '"><i class="md-icon">' + button.icon + "</i></button>"
				}
				return html
			}(options)), !1 !== options.enableUserDataButtons && (likes = null == (userData = item.UserData || {}).Likes ? "" : userData.Likes, userDataButtonsHtml = "", itemHelper.canMarkPlayed(item) && (userDataButtonsHtml += '<button type="button" is="emby-playstatebutton" type="button" class="listItemButton paper-icon-button-light" data-id="' + item.Id + '" data-serverid="' + item.ServerId + '" data-itemtype="' + itemType + '" data-played="' + userData.Played + '"><i class="md-icon">&#xE5CA;</i></button>'), itemHelper.canRate(item) && (userDataButtonsHtml += '<button type="button" is="emby-ratingbutton" type="button" class="listItemButton paper-icon-button-light" data-id="' + item.Id + '" data-serverid="' + item.ServerId + '" data-itemtype="' + itemType + '" data-likes="' + likes + '" data-isfavorite="' + userData.IsFavorite + '"><i class="md-icon">&#xE87D;</i></button>'), userDataButtonsHtml && (html += '<span class="listViewUserDataButtons flex align-items-center">' + userDataButtonsHtml + "</span>")), options.dragHandle && (html += '<i class="listViewDragHandle dragHandle md-icon listItemIcon listItemIcon-transparent">&#xE25D;</i>')), enableContentWrapper && (html += "</div>", enableOverview && item.Overview && (html += '<div class="listItem-bottomoverview secondaryText">', html += dom.htmlEncode(item.Overview), html += "</div>")), options.listItemParts) {
			var attributes = itemShortcuts.getShortcutAttributes(item, options);
			return action && attributes.push({
				name: "data-action",
				value: action
			}), attributes.push({
				name: "data-index",
				value: index
			}), options.addTabIndex && attributes.push({
				name: "tabindex",
				value: "0"
			}), options.draggable && attributes.push({
				name: "draggable",
				value: "true"
			}), {
				attributes: attributes,
				html: html
			}
		}
		var dataAttributes = itemShortcuts.getShortcutAttributesHtml(item, options);
		return action && (dataAttributes += ' data-action="' + action + '"'), dataAttributes += ' data-index="' + index + '"', options.addTabIndex && (dataAttributes += ' tabindex="0"'), options.draggable && (dataAttributes += ' draggable="true"'), "<" + tagName + ' class="' + options.className + '"' + dataAttributes + ">" + html + "</" + tagName + ">"
	}

	function setListOptions(items, options) {
		options.enableContentWrapper = options.enableOverview && !layoutManager.tv, options.containerAlbumArtistIds = (options.containerAlbumArtists || []).map(getId), options.enableSideMediaInfo = null == options.enableSideMediaInfo || options.enableSideMediaInfo, options.clickEntireItem = !!layoutManager.tv || !(options.mediaInfo || options.moreButton || options.enableUserDataButtons || options.addToListButton || options.enableSideMediaInfo || options.enableOverview), options.isLargeStyle = "large" === options.imageSize, options.action = options.action || "link", options.tagName = options.clickEntireItem ? "button" : "div", options.listItemBodyTagName = "div";
		var cssClass = "listItem";
		(options.border || !1 !== options.highlight && !layoutManager.tv) && (cssClass += " listItem-border"), options.clickEntireItem && (cssClass += " itemAction"), "div" === options.tagName && (cssClass += " focusable", options.addTabIndex = !0), "none" === options.action && !options.clickEntireItem || (cssClass += " listItemCursor"), layoutManager.tv ? cssClass += " listItem-focusscale" : (cssClass += " listItem-touchzoom", cssClass += " listItem-touchzoom-transition"), layoutManager.tv || (options.draggable = !1 !== options.draggable, options.draggableSubItems = options.draggable && !1 !== options.draggableSubItems), options.isLargeStyle && (cssClass += " listItem-largeImage"), options.enableContentWrapper && (cssClass += " listItem-withContentWrapper"), !1 === options.verticalPadding && (cssClass += " listItem-noverticalpadding"), options.itemClass && (cssClass += " " + options.itemClass), options.dragHandle && options.draggable ? cssClass += " drop-target ordered-drop-target" : options.dropTarget && !layoutManager.tv && (cssClass += " drop-target full-drop-target"), options.className = cssClass;
		var imageContainerClass, innerHTML = "";
		!1 !== options.image && (imageContainerClass = "listItemImageContainer", options.isLargeStyle && (imageContainerClass += " listItemImageContainer-large", layoutManager.tv && (imageContainerClass += " listItemImageContainer-large-tv")), innerHTML += '<div class="' + imageContainerClass + '"></div>'), innerHTML += "<" + options.listItemBodyTagName + ' class="listItemBody">';
		var textlines = [];
		options.showDateModified && textlines.push("&nbsp;"), options.showDateCreated && textlines.push("&nbsp;"), options.showDate && textlines.push("&nbsp;"), options.showShortOverview && textlines.push("&nbsp;"), options.showProgramDateTime && textlines.push("&nbsp;"), options.showProgramTime && textlines.push("&nbsp;"), options.showChannel && textlines.push("&nbsp;"), options.showLogLine && textlines.push("&nbsp;"), options.showAccessToken && textlines.push("&nbsp;"), (options.showParentTitle && options.parentTitleWithTitle || options.showParentTitle) && textlines.push("&nbsp;"), options.parentTitleWithTitle || textlines.push("&nbsp;"), textlines.length < 1 && textlines.push("&nbsp;"), textlines.length < 2 && textlines.push("&nbsp;"), innerHTML += getTextLinesHtml(textlines, options.isLargeStyle, options.allowTextWrap), options.enableOverview && (innerHTML += '<div class="listItem-overview listItemBodyText listItemBodyText-secondary">', !1 !== options.mediaInfo && (options.enableSideMediaInfo || (innerHTML += '<div class="listItemMediaInfo listItemBodyText listItemBodyText-secondary listItemBodyText-nowrap"></div>')), innerHTML += "</div>"), innerHTML += "</" + options.listItemBodyTagName + ">", options.dragHandle && (innerHTML += '<i class="listViewDragHandle dragHandle md-icon listItemIcon listItemIcon-transparent">&#xE25D;</i>'), options.templateInnerHTML = innerHTML
	}

	function getListViewHtml(items, options) {
		setListOptions(0, options);
		for (var groupTitle = "", html = "", i = 0, length = items.length; i < length; i++) {
			var itemGroupTitle, item = items[i];
			!options.showIndex || (itemGroupTitle = function(item, options) {
				if ("disc" !== options.index) return "";
				var parentIndexNumber = item.ParentIndexNumber;
				return 1 === parentIndexNumber || null == parentIndexNumber ? "" : globalize.translate("ValueDiscNumber", parentIndexNumber)
			}(item, options)) !== groupTitle && (html += 0 === i ? '<h2 class="listGroupHeader listGroupHeader-first">' : '<h2 class="listGroupHeader">', html += itemGroupTitle, html += "</h2>", groupTitle = itemGroupTitle), html += getListItemHtml(item, i, options)
		}
		return html
	}
	return supportsNativeLazyLoading = !1, {
		getListViewHtml: getListViewHtml,
		getItemsHtml: getListViewHtml,
		getListItemHtml: getListItemHtml,
		setListOptions: setListOptions,
		getItemParts: function(item, index, options) {
			return options.listItemParts = !0, getListItemHtml(item, index, options)
		},
		buildItems: function(items, options) {
			var itemsContainer = options.itemsContainer;
			if (document.body.contains(itemsContainer)) {
				var parentContainer = options.parentContainer;
				if (parentContainer) {
					if (!items.length) return void parentContainer.classList.add("hide");
					parentContainer.classList.remove("hide")
				}
				var html = getListViewHtml(items, options);
				itemsContainer.innerHTML = html, itemsContainer.items = items, html && imageLoader.lazyChildren(itemsContainer), options.autoFocus && focusManager.autoFocus(itemsContainer)
			}
		}
	}
});