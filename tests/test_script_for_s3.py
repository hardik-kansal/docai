import json
import requests

# 1. Your raw JSON response from the API
api_response = {
    "upload_url": '{"url": "http://localhost:9000/contracts", "fields": {"key": "uploads/ab0b00856e464dd1965bea5ffd3aaaf5/207c1be2-e9b2-4a93-9850-7ea7c2be5261/hardik", "Content-Type": "application/pdf", "acl": "private", "AWSAccessKeyId": "hardik", "policy": "eyJleHBpcmF0aW9uIjogIjIwMjYtMDctMDFUMTY6NTM6NTFaIiwgImNvbmRpdGlvbnMiOiBbeyJrZXkiOiAidXBsb2Fkcy9hYjBiMDA4NTZlNDY0ZGQxOTY1YmVhNWZmZDNhYWFmNS8yMDdjMWJlMi1lOWIyLTRhOTMtOTg1MC03ZWE3YzJiZTUyNjEvaGFyZGlrIn0sIFsiY29udGVudC1sZW5ndGgtcmFuZ2UiLCAxLCAyMTQ2NDQ3MzAzXSwgWyJlcSIsICIkQ29udGVudC1UeXBlIiwgImFwcGxpY2F0aW9uL3BkZiJdLCB7ImFjbCI6ICJwcml2YXRlIn0sIHsiYnVja2V0IjogImNvbnRyYWN0cyJ9LCB7ImtleSI6ICJ1cGxvYWRzL2FiMGIwMDg1NmU0NjRkZDE5NjViZWE1ZmZkM2FhYWY1LzIwN2MxYmUyLWU5YjItNGE5My05ODUwLTdlYTdjMmJlNTI2MS9oYXJkaWsifV19", "signature": "eZJvv+VVIIl3882Z+MBr2rtKFuw="}}',
    "object_key": "uploads/ab0b00856e464dd1965bea5ffd3aaaf5/207c1be2-e9b2-4a93-9850-7ea7c2be5261/hardik",
    "expires_in": 9000,
}

# json releases \ too
s3_data = json.loads(api_response["upload_url"])
upload_url = s3_data["url"]
form_fields = s3_data["fields"]

local_file_path = "test.pdf"


try:
    with open(local_file_path, "rb") as file_stream:
        # CRITICAL RULE: The file data tuple MUST be the last item in the list!
        multipart_form_data = []

        # Add authentication settings first
        for key, value in form_fields.items():
            multipart_form_data.append((key, (None, value)))

        # Add raw file stream last
        multipart_form_data.append(
            ("file", (local_file_path, file_stream, "application/pdf"))
        )

        # 6. Execute the direct POST request to MinIO/S3
        # Note: Do NOT add a 'headers' argument here. requests sets it natively.
        response = requests.post(upload_url, files=multipart_form_data)

    # 7. Evaluate response status codes
    if response.status_code == 204:
        print(" Success! File uploaded directly to MinIO storage container.")
    else:
        print(f"❌ Upload Failed. Status Code: {response.status_code}")
        print(f"Server Error Message Summary:\n{response.text}")

except FileNotFoundError:
    print(
        f"❌ Error: Please create or provide a valid PDF file at '{local_file_path}' to run this test."
    )
except Exception as error:
    print(f"❌ Network connection issue encountered: {error}")


"""

POST /contracts HTTP/1.1
Host: localhost:9000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryXYZ
<!-- End of Global Request Headers -->

------WebKitFormBoundaryXYZ
Content-Disposition: form-data; name="key"

uploads/ab0b00856e464dd1965...
------WebKitFormBoundaryXYZ
Content-Disposition: form-data; name="Content-Type"

application/pdf
------WebKitFormBoundaryXYZ
Content-Disposition: form-data; name="acl"

private
------WebKitFormBoundaryXYZ
Content-Disposition: form-data; name="file"; filename="my_contract.pdf"
Content-Type: application/pdf

[Raw Binary Bytes of the File]
------WebKitFormBoundaryXYZ--


"""
