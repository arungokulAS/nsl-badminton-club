document.addEventListener('DOMContentLoaded', function() {
    function fetchTeams() {
        fetch('/api/public/teams/')
            .then(response => response.json())
            .then(data => {
                const tbody = document.querySelector('#teams-table-body');
                if (!tbody) return;
                tbody.innerHTML = '';
                data.teams.forEach(team => {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td>${team.team_name}</td><td>${team.player1_name || ''}</td><td>${team.player2_name || ''}</td>`;
                    tbody.appendChild(row);
                });
            });
    }
    fetchTeams();
    setInterval(fetchTeams, 15000);
});
