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
        $.get(app.domain + '/keyword', {keyword:term,size:count}, function(data) {
            $div.attr('data-count', data.matched);
            var inserted = false;
            var charts = $(".charts .chart").get();
            for (var ii = 0; ii < charts.length; ii++) {
                $this = $(charts[ii]);
                var count = $this.attr('data-count');
                if (data.matched > count) {
                    console.log(term + ": " + data.matched  + " is more than " + count + "; inserting before");
                    $this.before($div);
                    inserted = true;
                    break;
                }
            }
            if (!inserted) {
                $(".charts").append($div);
            }
            var matched = {
                chart: {
                    type: 'pie'
                },
                title: {
                    text: "<b>" + data.keyword + "</b> found in <br><a class='load-keyword-all' data-keyword='" + data.keyword + "' href='#'>" + data.matched.toLocaleString() + "</a> documents",
                    useHTML: true,
                    align: "left"
                },
                subtitle: {
                    text: "" + (Math.floor((data.matched / data.all) * 10000) / 100) + "% of all documents",
                    align: "left"
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
                    text: "Top sites for <b>" + data.keyword + "</b>:"
                },
                legend: {
                    align: 'right',
                    verticalAlign: 'top',
                    layout: 'vertical',
                    y: 20
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

    $('body').on('click', '.load-keyword-all', function() {
        return false; 
    });

    $('body').on('click', '.load-terms', function() {
        var terms = $('.terms-list').val().split('\n');
        $(".charts .chart").addClass('dirty');
        for (var ii = 0; ii < terms.length; ii++) {
            var term = terms[ii];
            var slug = "terms-" + slugify(term);
            if (slug == 'terms-')
                continue;
            if ($("#" + slug).length) {
                if ($("#" + slug + " .highcharts-container").length) {
                    $("#" + slug).removeClass('dirty');
                } else {
                    $("#" + slug).remove();
                    loadCharts(term);
                }
            } else {
                loadCharts(term);
            }
        }
        $(".charts .dirty").remove();
        return false;
    });
	
})(jQuery);
