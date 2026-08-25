
document.addEventListener('DOMContentLoaded', () => {
const buildingSelect = document.getElementById('building-select');
    if (buildingSelect) {
        const roomSelect = document.getElementById('room-select');

        const populateDropdown = (selectElement, items, defaultOptionText) => {
            selectElement.innerHTML = `<option value="">${defaultOptionText}</option>`;
            items.forEach(item => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.room;
                selectElement.appendChild(option);
            });
            selectElement.disabled = false;
        };

        buildingSelect.addEventListener('change', async () => {
            const buildingId = buildingSelect.value;

            roomSelect.innerHTML = '<option value="">Select a building first</option>';
            roomSelect.disabled = false;

            if (buildingId) {
                try {
                    const response = await fetch(`/api/rooms/${buildingId}`);
                    const data = await response.json();
                    populateDropdown(roomSelect, data.rooms, 'Select a room');
                } catch (error) {
                    console.error('Failed to fetch rooms:', error);
                }
            }
        });
    }
});
