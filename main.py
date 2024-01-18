from flask import Flask, Response, request
from img2table.document import PDF
from img2table.ocr import TesseractOCR


app = Flask(__name__)

ARG_PAGE = 'page'
ARG_MIN_CONFIDENCE = 'min_confidence'
ARG_IMPLICIT_ROWS = 'implicit_rows'
ARG_BORDERLESS_TABLES = 'borderless_tables'
ARG_LANG = 'lang'

ARG_FILE = 'file'

@app.route("/health", methods=["GET"])
def health() -> Response:
    return Response(status=200)

@app.route("/extract/pdf", methods=["POST"])
def extract_pdf() -> Response:
    rsp = Response(mimetype='text/plain')
    file = request.files.get(ARG_FILE)
    if file is None:
        rsp.status_code = 400
        rsp.response = "file required"
        return rsp
    lang = request.args.get(ARG_LANG, "rus", type=str)
    page = request.args.get(ARG_PAGE, None, type=int)
    implicit_rows = True if request.args.get(ARG_IMPLICIT_ROWS, False, type=str) == "true" else False
    borderless_tables = True if request.args.get(ARG_BORDERLESS_TABLES, False, type=str) == "true" else False
    min_confidence = request.args.get(ARG_MIN_CONFIDENCE, 90, type=int)
    if min_confidence < 0 or min_confidence > 99:
        rsp.status_code = 400
        rsp.response = "min_comfidence range 0..99"
        return rsp

    pages = None if page is None else [page]
    pdf = PDF(file.stream.read(), pages=pages, detect_rotation=False, pdf_text_extraction=True)
    ocr = TesseractOCR(n_threads=1, lang=lang)
    try:
        tables = pdf.extract_tables(
            ocr=ocr,
            implicit_rows=implicit_rows,
            borderless_tables=borderless_tables,
            min_confidence=min_confidence,
        )
    except ValueError as e:
        rsp.status_code = 400
        rsp.response = str(e)
        return rsp
    except Exception as e:
        raise e
    
    for page_idx in tables:
        extracted_tables = tables[page_idx]
        for table in extracted_tables:
            rows:dict[int,list[str]] = dict()
            extracted_rows = table.content.values()
            for cells in extracted_rows:
                for cell in cells:
                    y = cell.bbox.y1
                    if y not in rows:
                        rows[y] = list()
                    rows[y].append(cleanup_value(cell.value))
            # reindex rows for cleanup possible, cuz indexes are y coordinates on page
            indexed_rows:list[list[str]] = list()
            for idx in rows:
                indexed_rows.append(rows[idx])

            headers = ",".join(indexed_rows[0])
            iteration = 0
            for row in cleanup_rows(indexed_rows):
                val = ",".join(row)
                # split tables that were detected as single
                if val == headers and iteration > 0:
                    rsp.response += "\n\n"
                rsp.response += val + "\n"
                iteration+=1

            rsp.response += "\n\n"
    
    rsp.mimetype = "text/csv"
    rsp.headers.add("Content-Disposition", f"attachment;filename={file.filename}.csv")
    # clean last two newlines
    rsp.response = rsp.response[:-2]
    return rsp

def cleanup_value(value:str) -> str:
    if value is not None and value.__contains__(","):
        value = f"\"{value}\""
    return value.replace("\n", " ")

# AS IS:
# 
# H1,   H2, H3
# Y,    x1, x2, Y,Y,...*rows down
# x3,   x4
# x5,   x6

# TO BE:
# H1,   H2, H3
# Y,    x1, x2
# Y,    x3, x4
# Y,    x5, x6
def cleanup_rows(ir:list[list[str]]) ->list[list[str]]:
    if len(ir) < 3:
        return ir
    row_length:int = 0
    rest:list[str] = []

    for row_idx in range(len(ir)):
        if row_length == 0:
            row_length = len(ir[row_idx])
            rest = ir[row_idx+1][row_length:]
            ir[row_idx+1] = ir[row_idx+1][:row_length]
            continue
        if len(ir[row_idx]) == row_length:
            continue
        if len(rest) > 0:
            ir[row_idx].insert(0, rest.pop())
        if len(rest) == 0:
            row_length = 0

    return ir
if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0", debug=False)