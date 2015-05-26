/*
	Striped by Pixelarity
	pixelarity.com @pixelarity
	License: pixelarity.com/license
*/

(function($) {
    var app = { pagesize: 20 };

	skel.breakpoints({
		desktop: '(min-width: 737px)',
		wide: '(min-width: 1201px)',
		narrow: '(min-width: 737px) and (max-width: 1200px)',
		narrower: '(min-width: 737px) and (max-width: 1000px)',
		mobile: '(max-width: 736px)'
	});

	$(function() {

		var	$window = $(window),
			$body = $('body'),
			$document = $(document);

		// Disable animations/transitions until the page has loaded.
			$body.addClass('is-loading');

			$window.on('load', function() {
				$body.removeClass('is-loading');
			});

		// Fix: Placeholder polyfill.
			$('form').placeholder();

		// Prioritize "important" elements on mobile.
			skel.on('+mobile -mobile', function() {
				$.prioritize(
					'.important\\28 mobile\\29',
					skel.breakpoint('mobile').active
				);
			});

		// Off-Canvas Sidebar.

			// Height hack.
				var $sc = $('#sidebar, #content'), tid;

				$window
					.on('resize', function() {
						window.clearTimeout(tid);
						tid = window.setTimeout(function() {
							$sc.css('min-height', $document.height());
						}, 100);
					})
					.on('load', function() {
						$window.trigger('resize');
					})
					.trigger('resize');

			// Title Bar.
				$(
					'<div id="titleBar">' +
						'<a href="#sidebar" class="toggle"></a>' +
						'<span class="title">' + $('#logo').html() + '</span>' +
					'</div>'
				)
					.appendTo($body);

			// Sidebar
				$('#sidebar')
					.panel({
						delay: 500,
						hideOnClick: true,
						hideOnSwipe: true,
						resetScroll: true,
						resetForms: true,
						side: 'left',
						target: $body,
						visibleClass: 'sidebar-visible'
					});

			// Fix: Remove navPanel transitions on WP<10 (poor/buggy performance).
				if (skel.vars.os == 'wp' && skel.vars.osVersion < 10)
					$('#titleBar, #sidebar, #main')
						.css('transition', 'none');

	});

    //helpers
    app.load = function(fragments) {
        $("#context").load(app.url, function() {
            for (var ii = 0; ii < fragments.length; ii++) {
                $("#" + fragments[ii]).html($("#" + fragments[ii], "#context").html());
            }
            $("#context").empty();
        });
    };

    $(function() {
        
        //event handlers
        $('#sidebar, #content').on("click", '.go-home', function() {
            window.location.reload();
        });

        $('#sidebar, #content').on("click", ".set-domain", function() {
            app.domain = $(this).attr("data-key");
            app.page = 0;
            app.filter = "";
            app.url = "domain/" + app.domain + "?d=" + app.pagesize;
            app.load(["content", "nav", "domain-sidebar"]);
        });

        $('#sidebar, #content').on('click', '.filter-domain', function() {
            app.page = 0;
            app.filter = $(this).attr('data-field') + ":" + $(this).attr('data-key');
            app.url = "domain/" + app.domain + "?f=" + app.filter + "&d=" + app.pagesize + "&o=" + app.pagesize * app.page;
            app.load(["content", "nav", "domain-sidebar"]);
        });

        $('#content').on('click', '.load-next', function() {
            app.page += 1;
            app.url = "domain/" + app.domain + "?f=" + app.filter + "&d=" + app.pagesize + "&o=" + app.pagesize * app.page;
            app.load(["content", "nav", "domain-sidebar"]);
            return false;
        });

        $('#content').on('click', '.load-prev', function() {
            app.page -= 1;
            app.url = "domain/" + app.domain + "?f=" + app.filter + "&d=" + app.pagesize + "&o=" + app.pagesize * app.page;
            app.load(["content", "nav", "domain-sidebar"]);
            return false;
        });
        
        //init
        $("a.set-domain").first().click();
    });

})(jQuery);
