/**
 * admin_live_tracker.js
 * Auto-refresh admin Booking table with live tracker + status updates.
 */

document.addEventListener("DOMContentLoaded", () => {
  console.log("📡 Admin live tracker initialized");
  console.log("⏳ Auto-refreshing booking locations every 10s...");

  // How often to refresh (in milliseconds)
  const REFRESH_INTERVAL = 10000;

  /**
   * Fetch latest tracker data for a booking
   */
  async function fetchTrackerData(bookingId) {
    try {
      // Adjust path based on your admin URL (use /dj-admin/ if customized)
      const res = await fetch(`/admin/core/booking/${bookingId}/pings/`);
      if (!res.ok) return null;
      return await res.json();
    } catch (error) {
      console.warn(`❌ Failed to fetch tracker data for booking ${bookingId}:`, error);
      return null;
    }
  }

  /**
   * Update the booking row in the admin list view
   */
  async function updateBookingRow(row, bookingId) {
    const data = await fetchTrackerData(bookingId);
    if (!data) return;

    // Find columns
    const cols = row.querySelectorAll("td");
    let statusCell = null;
    let locationCell = null;

    // Identify cells dynamically by matching text headers
    const headerCells = document.querySelectorAll("thead th");
    headerCells.forEach((th, index) => {
      const headerText = th.textContent.trim().toLowerCase();
      if (headerText.includes("status")) statusCell = cols[index];
      if (headerText.includes("location")) locationCell = cols[index];
    });

    // Update location
    if (locationCell) {
      if (data.latitude && data.longitude) {
        locationCell.innerHTML = `<span style="color:#007bff;">${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}</span>`;
      } else {
        locationCell.innerHTML = `<span style="color:#999;">No data</span>`;
      }
    }

    // Update status
    if (statusCell && data.status) {
      let color = "#6c757d";
      if (data.status === "Pending") color = "#f39c12";
      if (data.status === "Confirmed") color = "#17a2b8";
      if (data.status === "En Route") color = "#007bff";
      if (data.status === "Delivered") color = "#28a745";
      statusCell.innerHTML = `<b style="color:${color};">${data.status}</b>`;
    }

    console.log(`✅ Booking #${bookingId} updated: ${data.status || "No status"}`);
  }

  /**
   * Loop through all booking rows and refresh them
   */
  async function refreshAllBookings() {
    const rows = document.querySelectorAll("tr.model-booking");
    for (const row of rows) {
      const idCell = row.querySelector("th a");
      if (!idCell) continue;
      const bookingId = idCell.textContent.trim();
      if (!/^\d+$/.test(bookingId)) continue;
      await updateBookingRow(row, bookingId);
    }
  }

  /**
   * Initialize polling
   */
  function startAutoRefresh() {
    refreshAllBookings();
    setInterval(refreshAllBookings, REFRESH_INTERVAL);
  }

  // Only run if we are on Booking list page
  if (document.querySelector("body.model-booking.change-list")) {
    startAutoRefresh();
  }
});
