/**
 * Date Range Picker Utility
 * Provides a unified interface for initializing and handling date range pickers
 */

export function initDateRangePicker({
  elementSelector,
  startDate,
  endDate,
  ranges,
  onApply
}) {
  $(elementSelector).daterangepicker({
    startDate,
    endDate,
    ranges,
    opens: 'left',
    alwaysShowCalendars: true,
    locale: {
      format: 'MMM D, YYYY',
      cancelLabel: 'Clear'
    }
  }, function(start, end, label) {
    if (typeof onApply === 'function') {
      onApply(start, end, label);
    }
  });
}

export function updateDateRangeDisplay({
  elementSelector,
  startDate,
  endDate,
  format = 'MMM D, YYYY'
}) {
  const rangeText = `${startDate.format(format)} - ${endDate.format(format)}`;
  $(elementSelector).html(rangeText);
}
