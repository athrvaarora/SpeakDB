// Database logos as SVG for database selection page

/**
 * Get an SVG logo for the specified database type
 * @param {string} dbType - The database type
 * @returns {string} - SVG logo HTML
 */
function getDatabaseLogo(dbType) {
    // SVG container with standard sizing
    const svgWrapper = `<div class="db-logo">${getLogoSvg(dbType)}</div>`;
    return svgWrapper;
}

/**
 * Get the raw SVG for the specified database type
 * @param {string} dbType - The database type
 * @returns {string} - SVG markup
 */
function getLogoSvg(dbType) {
    // Define simple SVG logos for each database type
    // These are simplified versions that capture the essence of each database logo
    // while keeping the file size small
    
    switch (dbType) {
        case 'postgresql':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 2C9.373 2 4 7.373 4 14C4 20.627 9.373 26 16 26C22.627 26 28 20.627 28 14C28 7.373 22.627 2 16 2Z" fill="#336791"/>
                <path d="M19.5 9.5C19.5 10.881 18.381 12 17 12C15.619 12 14.5 10.881 14.5 9.5C14.5 8.119 15.619 7 17 7C18.381 7 19.5 8.119 19.5 9.5Z" fill="white"/>
                <path d="M13 13C13 14.657 11.657 16 10 16C8.343 16 7 14.657 7 13C7 11.343 8.343 10 10 10C11.657 10 13 11.343 13 13Z" fill="white"/>
                <path d="M22 18C22 19.657 20.657 21 19 21C17.343 21 16 19.657 16 18C16 16.343 17.343 15 19 15C20.657 15 22 16.343 22 18Z" fill="white"/>
            </svg>`;
            
        case 'mysql':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 4L8 6V26L6 28H24L26 26V6L24 4H6Z" fill="#00618A"/>
                <path d="M16 10V22M12 10V22M20 10V22M8 16H24" stroke="white" stroke-width="2"/>
            </svg>`;
            
        case 'sqlserver':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="5" y="5" width="22" height="22" rx="2" fill="#A91D22"/>
                <path d="M8 12H24V20H8V12Z" fill="white"/>
                <path d="M13 12V20M19 12V20M8 16H24" stroke="#A91D22" stroke-width="1.5"/>
            </svg>`;
            
        case 'oracle':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="6" y="6" width="20" height="20" rx="2" fill="#F80000"/>
                <path d="M10 14H22V18H10V14Z" fill="white"/>
            </svg>`;
            
        case 'sqlite':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4C10.477 4 6 8.477 6 14V18C6 23.523 10.477 28 16 28C21.523 28 26 23.523 26 18V14C26 8.477 21.523 4 16 4Z" fill="#0F80CC"/>
                <rect x="12" y="12" width="8" height="8" fill="white"/>
            </svg>`;
            
        case 'redshift':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 5L7 11V21L16 27L25 21V11L16 5Z" fill="#205B97"/>
                <path d="M16 5V15M16 15L7 21M16 15L25 21" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        case 'cloudsql':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 10C6 7.791 7.791 6 10 6H22C24.209 6 26 7.791 26 10V22C26 24.209 24.209 26 22 26H10C7.791 26 6 24.209 6 22V10Z" fill="#4285F4"/>
                <rect x="10" y="12" width="12" height="8" fill="white"/>
                <path d="M13 12V20M19 12V20M10 16H22" stroke="#4285F4" stroke-width="1.5"/>
            </svg>`;
            
        case 'mariadb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 6C6 4.895 6.895 4 8 4H24C25.105 4 26 4.895 26 6V26C26 27.105 25.105 28 24 28H8C6.895 28 6 27.105 6 26V6Z" fill="#003545"/>
                <path d="M11 10L13 12V20L11 22M21 10L19 12V20L21 22" stroke="#C0765A" stroke-width="2"/>
                <path d="M13 16H19" stroke="#C0765A" stroke-width="2"/>
            </svg>`;
            
        case 'db2':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="6" y="6" width="20" height="20" rx="2" fill="#052FAD"/>
                <path d="M10 12H22V20H10V12Z" fill="white"/>
                <path d="M14 12V20M18 12V20" stroke="#052FAD" stroke-width="1.5"/>
            </svg>`;
            
        case 'mongodb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4V28" stroke="#10AA50" stroke-width="8" stroke-linecap="round"/>
                <path d="M16 4C14 8 8 12 8 18C8 22 10 26 16 28" stroke="#B8C4C2" stroke-width="1"/>
            </svg>`;
            
        case 'cassandra':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4L4 10L16 16L28 10L16 4Z" fill="#1287B1"/>
                <path d="M16 16V28" stroke="#1287B1" stroke-width="4" stroke-linecap="round"/>
                <path d="M4 10V22L16 28" stroke="#1287B1" stroke-width="1"/>
                <path d="M28 10V22L16 28" stroke="#1287B1" stroke-width="1"/>
            </svg>`;
            
        case 'redis':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 7L9 10L16 13L23 10L16 7Z" fill="#A41E11"/>
                <path d="M16 13L9 16L16 19L23 16L16 13Z" fill="#A41E11"/>
                <path d="M16 19L9 22L16 25L23 22L16 19Z" fill="#A41E11"/>
            </svg>`;
            
        case 'elasticsearch':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 16H26" stroke="#FEC514" stroke-width="4" stroke-linecap="round"/>
                <path d="M12 8H26" stroke="#FEC514" stroke-width="4" stroke-linecap="round"/>
                <path d="M12 24H26" stroke="#FEC514" stroke-width="4" stroke-linecap="round"/>
            </svg>`;
            
        case 'dynamodb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 5L6 9V23L16 27L26 23V9L16 5Z" fill="#4053D6"/>
                <path d="M16 12C19.314 12 22 10.657 22 9C22 7.343 19.314 6 16 6C12.686 6 10 7.343 10 9C10 10.657 12.686 12 16 12Z" fill="white"/>
                <path d="M16 18C19.314 18 22 16.657 22 15C22 13.343 19.314 12 16 12C12.686 12 10 13.343 10 15C10 16.657 12.686 18 16 18Z" fill="white"/>
                <path d="M16 24C19.314 24 22 22.657 22 21C22 19.343 19.314 18 16 18C12.686 18 10 19.343 10 21C10 22.657 12.686 24 16 24Z" fill="white"/>
                <path d="M10 9V21M22 9V21" stroke="#4053D6" stroke-width="0.5"/>
            </svg>`;
            
        case 'couchbase':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 16C5 10.477 9.477 6 15 6H26V17C26 22.523 21.523 27 16 27H5V16Z" fill="#EA2328"/>
                <path d="M8 13C8 12.448 8.448 12 9 12H14C14.552 12 15 12.448 15 13V18C15 18.552 14.552 19 14 19H9C8.448 19 8 18.552 8 18V13Z" fill="white"/>
                <path d="M17 13C17 12.448 17.448 12 18 12H23C23.552 12 24 12.448 24 13V18C24 18.552 23.552 19 23 19H18C17.448 19 17 18.552 17 18V13Z" fill="white"/>
            </svg>`;
            
        case 'neo4j':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="16" cy="10" r="6" fill="#008CC1"/>
                <circle cx="10" cy="22" r="6" fill="#008CC1"/>
                <circle cx="22" cy="22" r="6" fill="#008CC1"/>
                <path d="M16 10L10 22M16 10L22 22M10 22H22" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        case 'snowflake':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4V28M4 16H28M8 8L24 24M24 8L8 24" stroke="#29B5E8" stroke-width="2" stroke-linecap="round"/>
                <circle cx="16" cy="16" r="3" fill="#29B5E8"/>
            </svg>`;
            
        case 'bigquery':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 8H24L16 24L8 8Z" fill="#4285F4"/>
                <rect x="12" y="4" width="8" height="8" fill="#669DF6"/>
                <path d="M12 20H20V28H12V20Z" fill="#1A73E8"/>
            </svg>`;
            
        case 'synapse':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 7H28V13H4V7Z" fill="#0078D4"/>
                <path d="M4 15H18V21H4V15Z" fill="#0078D4"/>
                <path d="M4 23H12V29H4V23Z" fill="#0078D4"/>
                <path d="M20 15H28V29H20V15Z" fill="#0078D4"/>
            </svg>`;
            
        case 'cosmosdb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="16" cy="16" r="11" fill="#3999C6"/>
                <path d="M16 5V27M5 16H27M8.5 8.5L23.5 23.5M23.5 8.5L8.5 23.5" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        case 'firestore':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 6L14 18L6 30H26L18 18L26 6H6Z" fill="#F57C00"/>
                <path d="M6 6L14 18L6 30" stroke="#FFA000" stroke-width="1.5"/>
                <path d="M26 6L18 18L26 30" stroke="#FFCA28" stroke-width="1.5"/>
            </svg>`;
            
        case 'influxdb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <polygon points="4,22 16,4 28,22 16,28" fill="#22ADF6"/>
                <path d="M4 22L16 4L28 22L16 28L4 22Z" stroke="#22ADF6" stroke-width="0.5"/>
                <path d="M10 18L16 8L22 18" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        // New databases
        case 'supabase':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 8L10 4H26L22 8H6Z" fill="#3ECF8E"/>
                <path d="M6 8V24L10 28H26V12L22 8H6Z" fill="#3ECF8E"/>
                <path d="M14 16L18 12V20L14 24V16Z" fill="white"/>
            </svg>`;
            
        case 'teradata':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="6" y="6" width="20" height="20" rx="2" fill="#F8981D"/>
                <path d="M10 12H22M10 16H22M10 20H22" stroke="white" stroke-width="2" stroke-linecap="round"/>
            </svg>`;
            
        case 'saphana':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 8L16 4L28 8V24L16 28L4 24V8Z" fill="#0066B3"/>
                <path d="M16 10L10 12V20L16 22L22 20V12L16 10Z" fill="white"/>
            </svg>`;
            
        case 'planetscale':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4L28 16L16 28L4 16L16 4Z" fill="#0000FF"/>
                <circle cx="16" cy="16" r="6" fill="white"/>
            </svg>`;
            
        case 'vertica':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 6H26L16 26L6 6Z" fill="#7848AD"/>
            </svg>`;
            
        case 'timescaledb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 6L12 12H20L26 6H6Z" fill="#FDB515"/>
                <path d="M12 12V20L6 26V6L12 12Z" fill="#FDB515"/>
                <path d="M20 12V20L26 26V6L20 12Z" fill="#FDB515"/>
                <path d="M12 20L20 20L26 26H6L12 20Z" fill="#FDB515"/>
                <path d="M12 12H20V20H12V12Z" fill="#FDB515"/>
            </svg>`;
            
        case 'kdb':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 6H26V26H6V6Z" fill="#142E65"/>
                <path d="M10 10V22L16 16L10 10Z" fill="white"/>
                <path d="M16 10H22V16H16V10Z" fill="white"/>
                <path d="M16 16H22V22H16V16Z" fill="white"/>
            </svg>`;
            
        case 'tigergraph':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 16C5 10.477 9.477 6 15 6H26V17C26 22.523 21.523 27 16 27H5V16Z" fill="#FF6A00"/>
                <path d="M10 13L13 16L10 19M19 13L22 16L19 19" stroke="white" stroke-width="1.5"/>
                <path d="M13 16H19" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        case 'neptune':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4C9.373 4 4 9.373 4 16C4 22.627 9.373 28 16 28C22.627 28 28 22.627 28 16C28 9.373 22.627 4 16 4Z" fill="#2E27AD"/>
                <path d="M11 10L16 16L11 22M21 10L16 16L21 22" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        case 'heroku':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 6C6.895 6 6 6.895 6 8V24C6 25.105 6.895 26 8 26H24C25.105 26 26 25.105 26 24V8C26 6.895 25.105 6 24 6H8Z" fill="#430098"/>
                <path d="M12 22L12 16L10 18L12 22Z" fill="white"/>
                <path d="M20 22L20 16L22 18L20 22Z" fill="white"/>
                <path d="M16 16L16 10L20 16L16 22L12 16L16 10Z" fill="white"/>
            </svg>`;
            
        case 'crunchybridge':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="5" y="5" width="22" height="22" rx="2" fill="#27455C"/>
                <path d="M8 12H24V20H8V12Z" fill="#EF4925"/>
                <path d="M13 12V20M19 12V20" stroke="white" stroke-width="1.5"/>
            </svg>`;
            
        case 'neon':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4L4 16L16 28L28 16L16 4Z" fill="#00E699"/>
                <path d="M16 10L10 16L16 22L22 16L16 10Z" fill="white"/>
                <path d="M16 13L13 16L16 19L19 16L16 13Z" fill="#00E699"/>
            </svg>`;
            
        case 'prometheus':
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M16 4L8 12V20L16 28L24 20V12L16 4Z" fill="#E6522C"/>
                <path d="M16 8C12.686 8 10 10.686 10 14V18C10 21.314 12.686 24 16 24C19.314 24 22 21.314 22 18V14C22 10.686 19.314 8 16 8Z" fill="white"/>
                <path d="M16 12C14.895 12 14 12.895 14 14V18C14 19.105 14.895 20 16 20C17.105 20 18 19.105 18 18V14C18 12.895 17.105 12 16 12Z" fill="#E6522C"/>
            </svg>`;
            
        default:
            // Generic database icon for any unmatched database types
            return `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 8C6 6.895 6.895 6 8 6H24C25.105 6 26 6.895 26 8V24C26 25.105 25.105 26 24 26H8C6.895 26 6 25.105 6 24V8Z" fill="#666666"/>
                <rect x="10" y="10" width="12" height="4" rx="1" fill="white"/>
                <rect x="10" y="18" width="12" height="4" rx="1" fill="white"/>
            </svg>`;
    }
}
