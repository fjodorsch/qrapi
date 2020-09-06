from flask import Flask, request, render_template, abort, jsonify
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from pyzbar.pyzbar import decode
import pdf2image
import os


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'


class QReader:
    def __init__(self):
        self.tempdir = "/tmp"

    def get_qr(self, file: FileStorage):
        filename = secure_filename(file.filename)

        assert file.content_type == "application/pdf", \
            f"The content type of {file.content_type} not supported."

        # Save the file in a temporary folder
        filepath = os.path.join(self.tempdir, filename)
        file.save(filepath)

        pil_images = pdf2image.convert_from_path(
            filepath, dpi=200, output_folder=None, fmt='jpg', thread_count=1, strict=False
        )

        decoded = []
        for index, page_img in enumerate(pil_images):
            decoded.extend(
                [{"type": _.type, "data": _.data.decode("ascii"), "page": index} for _ in decode(image=page_img)]
            )

        return (decoded, len(pil_images))


# Instance of the QReader
qreader = QReader()


@app.route('/')
def document_upload():
    return render_template('upload.html', FLASK_ENV=os.environ.get("FLASK_ENV"))


def validate_header_auth(headers):
    environment_secret = os.getenv('API_AUTHORIZATION_TOKEN')
    assert headers.environ['HTTP_AUTHORIZATION'] == environment_secret, \
        "Wrong authorization token."


def json_abort(status_code, message):
    response = jsonify({'error': message})
    response.status_code = status_code
    abort(response)


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Validate that the request has a known token
        validate_header_auth(request.headers)

        return_list = []

        # Process the all files with the QReader class
        for listname, filelist in request.files.lists():
            for file in filelist:
                content, num_pages = qreader.get_qr(file=file)

                return_list.append({
                    "key": listname,
                    "filename": file.filename,
                    "num_pages": num_pages,
                    "content": content,
                })

        return jsonify(return_list)

    except Exception as e:
        json_abort(400, str(e))


if __name__ == '__main__':
    PORT = os.environ.get("PORT", 5001)
    app.run(port=PORT, host='0.0.0.0')
