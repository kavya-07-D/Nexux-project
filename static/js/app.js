document.addEventListener('DOMContentLoaded', () => {

    // ==============================
    // Mobile Menu
    // ==============================
    const menu = document.querySelector('.mobile-menu');
    const sidebar = document.querySelector('.sidebar');

    if (menu && sidebar) {
        menu.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // ==============================
    // Render Backend URL
    // ==============================
    const API_BASE_URL = 'https://nexux-project.onrender.com';


    // ==============================
    // Import File
    // ==============================
    const input = document.getElementById('import-file');

    if (input) {
        input.addEventListener('change', async () => {

            if (!input.files[0]) {
                return;
            }

            const body = new FormData();
            body.append('file', input.files[0]);

            try {

                const response = await fetch(
                    `${API_BASE_URL}/api/import`,
                    {
                        method: 'POST',
                        body: body
                    }
                );

                const result = await response.json();

                if (response.ok) {
                    alert(result.message || 'File imported successfully');
                } else {
                    alert(result.error || 'Import failed');
                }

            } catch (error) {

                console.error('Import error:', error);

                alert(
                    'Unable to connect to BankGuard backend.'
                );
            }
        });
    }


    // ==============================
    // Accent Color
    // ==============================
    document
        .querySelectorAll('[data-accent]')
        .forEach(button => {

            button.addEventListener('click', () => {

                const value = button.dataset.accent;

                const colors = {
                    mono: '#171716',
                    blue: '#426a92',
                    purple: '#785a88',
                    green: '#5d826b',
                    orange: '#bd784a'
                };

                document.documentElement.style.setProperty(
                    '--accent',
                    colors[value]
                );

                document
                    .querySelectorAll('[data-accent]')
                    .forEach(item => {

                        item.classList.toggle(
                            'active',
                            item === button
                        );

                    });

                localStorage.setItem(
                    'bankguard-accent',
                    value
                );
            });
        });


    // ==============================
    // Load Saved Accent Color
    // ==============================
    const saved = localStorage.getItem(
        'bankguard-accent'
    );

    if (saved) {

        const button = document.querySelector(
            `[data-accent="${saved}"]`
        );

        if (button) {
            button.click();
        }
    }

});
