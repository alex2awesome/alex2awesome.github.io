// Collapsible research-category cards and the "All Publications" tree, shared by
// research.html and music.html (markup: templates/includes/research_macros.html.j2;
// styles: assets/css/papers.css). Requires jQuery. Page-specific behaviour (lens
// switching, ?cat= deep links, #<lens>-paper-<id> hashes) lives in each page's own script.
(function ($) {
    function getUrlParameter(name) {
        name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
        var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
        var results = regex.exec(location.search);
        return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
    }

    // ---------- Category cards ----------
    function setCardOpen($card, open) {
        $card.toggleClass('open', open);
        $card.find('.category-summary').attr('aria-expanded', open ? 'true' : 'false');
        var $details = $card.find('.category-details').stop(true, true);
        if (open) { $details.slideDown(180); } else { $details.slideUp(180); }
    }

    // ---------- Publication tree ----------
    function setToggle($btn, open, animate) {
        $btn.attr('aria-expanded', open ? 'true' : 'false');
        var $body = $('#' + $btn.attr('aria-controls')).stop(true, true);
        if (animate === false) { $body.toggle(open); return; }
        if (open) { $body.slideDown(160); } else { $body.slideUp(160); }
    }

    // Expand every section containing the paper card `hash` points at (#<lens>-paper-<id>) and scroll to it.
    function revealPaper(hash) {
        if (!/^#[a-z]+-paper-[\w-]+$/.test(hash || '')) { return; }
        var $paper = $(hash);
        if (!$paper.length) { return; }
        $paper.parents('.pub-body').each(function () {
            setToggle($('.pub-toggle[aria-controls="' + this.id + '"]'), true, false);
        });
        $paper[0].scrollIntoView();
    }

    $(function () {
        $('.category-summary').on('click', function () {
            var $card = $(this).closest('.category-card');
            setCardOpen($card, !$card.hasClass('open'));
        });

        $('.pub-toggle').on('click', function () {
            var $btn = $(this);
            setToggle($btn, $btn.attr('aria-expanded') !== 'true');
        });

        $('.pub-expand-all').on('click', function (event) {
            event.preventDefault();
            $('.pub-toggle').each(function () { setToggle($(this), true); });
        });

        $('.pub-collapse-all').on('click', function (event) {
            event.preventDefault();
            $('.pub-toggle').each(function () { setToggle($(this), false); });
        });

        if (getUrlParameter('pubs') === 'all') {
            $('.pub-toggle').each(function () { setToggle($(this), true, false); });
        }
    });

    window.ResearchCards = {
        getUrlParameter: getUrlParameter,
        setCardOpen: setCardOpen,
        setToggle: setToggle,
        revealPaper: revealPaper
    };
})(jQuery);
