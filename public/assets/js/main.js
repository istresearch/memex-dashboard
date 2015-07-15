/*
	Striped by Pixelarity
	pixelarity.com @pixelarity
	License: pixelarity.com/license
*/

var app = { filter: { pagesize: 50 }, showSites: true };

(function($) {

	skel.breakpoints({
		desktop: '(min-width: 737px)',
		wide: '(min-width: 1201px)',
		narrow: '(min-width: 737px) and (max-width: 1200px)',
		narrower: '(min-width: 737px) and (max-width: 1000px)',
		mobile: '(max-width: 736px)'
	});

	app.bootstrap = function() {

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

	};

	app.mainPage = function() {
        app.bootstrap();

        //event handlers
        $('#sidebar, #content').on("click", '.go-home', function() {
            window.location.reload();
        });

        $('#sidebar, #content').on("click", ".set-domain", function() {
            app.filter.page = 0;
            app.filter.domain = $(this).attr("data-key");
            app.load();
            return false;
        });

        $('#sidebar, #content').on('click', '.add-filter', function() {
            app.filter.page = 0;
            app.filter[$(this).attr('data-field')] = $(this).attr('data-key');
            app.load();
            return false;
        });

        $('#sidebar, #content').on('click', '.remove-filter', function() {
            app.filter.page = 0;
            app.filter[$(this).attr('data-field')] = $(this).attr('data-key');
            app.load();
            return false;
        });

        $('#sidebar, #content').on('click', '.load-next', function() {
            app.filter.page += 1;
            app.load();
            return false;
        });

        $('#sidebar, #content').on('click', '.load-prev', function() {
            app.filter.page -= 1;
            app.load();
            return false;
        });

        $('#sidebar, #content').on('click', '.show-scrape', function() {
            var url = $(this).attr('href');
            $.get(url, function(data) {
                $.featherlight(data);
                $("#get").on('click', 'a.toggle', function() {
                    $(this).closest('div').find('pre').toggle();
                });
            });
            return false
        });

        $('#sidebar, #content').on('submit', '#search', function() {
            var query = $('#search input[name="query"]').val().replace(/\s+/g, '+');
            app.filter.page = 0;
            app.filter.phrase = query.length ? query : "";
            app.filter.exact = $('#search input[name="exact"]').prop('checked');
            app.load();
            return false;
        }); 

        $('#sidebar, #content').on('click', '.showSites', function() {
            app.showSites = !app.showSites;
            if (app.showSites) {
                $('.hosts').show();
            } else {
                $('.hosts').hide();
            }
            return false;
        });

        app.load = function() {
            $.post("./search/", app.filter, function(data) {
                $("#wrap").html(data);
                app.mainPage();
            });
        };

        if (app.showSites) {
            $('.hosts').show();
        } else {
            $('.hosts').hide();
        }
	};
	
})(jQuery);
