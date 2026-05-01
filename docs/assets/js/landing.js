$(function () {
  const $header = $('[data-elevate]');
  const $navToggle = $('.nav-toggle');
  const $siteNav = $('#site-nav');

  const elevateHeader = () => {
    $header.toggleClass('is-elevated', window.scrollY > 8);
  };

  elevateHeader();
  $(window).on('scroll', elevateHeader);

  $navToggle.on('click', function () {
    const isOpen = $siteNav.toggleClass('is-open').hasClass('is-open');
    $(this).attr('aria-expanded', String(isOpen));
  });

  $siteNav.find('a').on('click', function () {
    $siteNav.removeClass('is-open');
    $navToggle.attr('aria-expanded', 'false');
  });

  $('[data-tabs]').each(function () {
    const $tabs = $(this);
    const $buttons = $tabs.find('[role="tab"]');
    const $panels = $tabs.find('[role="tabpanel"]');

    $buttons.on('click', function () {
      const tabName = $(this).data('tab');

      $buttons.attr('aria-selected', 'false');
      $(this).attr('aria-selected', 'true');

      $panels.attr('hidden', true).removeClass('is-active');
      $tabs.find(`#panel-${tabName}`).removeAttr('hidden').addClass('is-active');
    });
  });

  $('.faq-list details').on('toggle', function () {
    if (!this.open) return;

    $('.faq-list details').not(this).removeAttr('open');
  });

  $('.copy-prompt').on('click', async function () {
    const $button = $(this);
    const target = $button.data('copy-target');
    const text = $(target).text().trim();

    try {
      await navigator.clipboard.writeText(text);
      $button.addClass('is-copied').text('已複製');
      setTimeout(() => {
        $button.removeClass('is-copied').text('複製 prompt');
      }, 1800);
    } catch {
      $button.text('請手動複製');
    }
  });
});
