var app = app || {};

(function($) {
    
    app.domain = $("body").attr('data-domain');

    var loadCharts = function(term) {
        var count = 5;
        var slug = "terms-" + slugify(term);
        var $div = $("<div class='chart' id='"+slug+"'>");
        $div.append("<div class='total'>");
        $div.append("<div class='sites'>");
        $div.append("<hr>");
        $(".charts").append($div);
        $.get(app.domain + '/keyword', {keyword:term,size:count}, function(data) {
            var matched = {
                chart: {
                    type: 'pie'
                },
                title: {
                    text: "<b>" + data.keyword + "</b> found in " + data.matched.toLocaleString() + " documents"
                },
                legend: {
                    align: 'right',
                },
                plotOptions: {
                    pie: {
                        dataLabels: {
                            enabled: false
                        }
                    }
                },
                series: [{
                    data: [
                        [ "other", data.all - data.matched ],
                        [ "matched", data.matched ]
                    ]
                }]
            };
            $("#"+slug+" .total").highcharts(matched);
            var sites = {
                chart: {
                    type: 'pie'
                },
                title: {
                    text: "Top sites with <b>" + data.keyword + "</b>"
                },
                legend: {
                    align: 'right',
                    verticalAlign: 'top',
                    layout: 'vertical',
                    x: 0,
                    y: 100
                },
                plotOptions: {
                    pie: {
                        dataLabels: {
                            enabled: false
                        },
                        showInLegend: true
                    }
                },
                series: [{
                    data: [ ]
                }]
            };
            for (key in data.sites) {
                sites.series[0].data.push([key, data.sites[key]]);
            }
            if (data.other) 
                sites.series[0].data.push(["other", data.other]);
            $("#"+slug+" .sites").highcharts(sites);
        });
    };
           
    var slugify = function(text) {
        return text.toString().toLowerCase().replace(/\s+/g, '-').replace(/[^\w\-]+/g, '').replace(/\-\-+/g, '-').replace(/^-+/, '').replace(/-+$/, '');
    };

    $('body').on('click', '.load-terms', function() {
        var terms = $('.terms-list').val().split('\n');
        $(".charts .chart").addClass('dirty');
        for (var ii = 0; ii < terms.length; ii++) {
            var term = terms[ii];
            var slug = "terms-" + slugify(term);
            if (slug == 'terms-')
                continue;
            if ($("#" + slug).length) {
                $("#" + slug).removeClass('dirty');
            } else {
                loadCharts(term);
            }
        }
        $(".charts .dirty").remove();
        return false;
    });
	
})(jQuery);
