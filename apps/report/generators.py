from openpyxl import Workbook


def generate_report_excel():
    from apps.report.models import Report
    r = Report.objects.get(id=2).sign_offs.first()

    headers, data, formulae = r.stat_conflict_country

    wb = Workbook()
    ws = wb.create_sheet('Flow Country')
    # primary headers and data
    for idx, (header_key, header_val) in enumerate(headers.items()):
        ws.cell(column=idx + 1, row=1, value=header_val)
        for idy, datum in enumerate(data):
            ws.cell(column=idx + 1, row=idy + 2, value=datum[header_key])
    # secondary headers and data
    for idx2, (header_key, formula) in enumerate(formulae.items()):
        # column starts at 1, hence idx+idx2+2
        ws.cell(column=idx + idx2 + 2, row=1, value=header_key)
        # list indexing starts at 0, hence idx+idx2+1
        for row, cell in enumerate(list(ws.columns)[idx + idx2 + 1], 1):
            if row == 1:
                continue
            cell.value = formula.format(row=row)
    wb.save(filename='temp.xlsx')
