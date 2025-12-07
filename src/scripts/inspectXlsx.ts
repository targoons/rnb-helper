import XLSX from 'xlsx';
import path from 'path';

const FILE = path.join(process.cwd(), 'src/data/raw/Move Changes.xlsx');

function inspect() {
    const workbook = XLSX.readFile(FILE);
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];

    // Get first row
    const headers = [];
    let col = 0;
    while (true) {
        const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
        const cell = sheet[cellAddress];
        if (!cell) break;
        headers.push(cell.v);
        col++;
    }

    console.log('Headers:', headers);

    // Print first few rows
    const data = XLSX.utils.sheet_to_json(sheet, { header: 1 });
    console.log('First 3 rows:', data.slice(0, 3));
}

inspect();
