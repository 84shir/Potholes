async function uploadFiles() {
    const files = document.getElementById('fileInput').files;

    for (let file of files) {
        const response = await fetch('/generate_presigned_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                'file_name': file.name,
                'file_type': file.type
            })
        });
        const data = await response.json()

        if (response.ok) {
            const presignedPostData = data.data;
            const formData = new FormData();
            Object.entries(presignedPostData.fields).forEach(([key, value]) => {
                formData.append(key, value);
            });
            formData.append('file', file)

            const uploadResponse = await fetch(presignedPostData.url, {
                method: 'POST',
                body: formData
            });

            if (uploadResponse.ok) {
                console.log('File ${file.name} uploaded');
            } else {
                console.error('Failed');
            }

        } else {
            console.error('Error presigned')
        }
    }
}

async function uploadDataset() {
    const kaggleUrl = document.getElementById('kaggleUrl').value;

    // Request presigned URLs for the dataset
    const response = await fetch('/generate_presigned_url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            'dataset_url': kaggleUrl
        })
    });

    const data = await response.json();

    if (response.ok) {
        const results = data.results;

        for (let entry of results) {
            const presignedData = entry; // Assuming the server returns a list of presigned URLs for all dataset files
            const { file_name, file_path, url, fields } = entry;

            // Prepare the form data for upload
            const formData = new FormData();
            Object.entries(entry.fields).forEach(([key, value]) => {
                formData.append(key, value);
            });

            // Fetch the file locally (if your server provides a local download mechanism for dataset files)
            const fileResponse = await fetch(`/local-files/${file_path}`);
            const fileBlob = await fileResponse.blob();
            formData.append('file', fileBlob, file_name);

            // Upload to S3 using the presigned URL
            const uploadResponse = await fetch(url, {
                method: 'POST',
                body: formData
            });

            if (uploadResponse.ok) {
                console.log(`File ${file_name} uploaded`);
                const tempClearResponse = await fetch(`/local-files/${file_path}`, {
                    method: 'DELETE',
                    body: formData
                });
                if (tempClearResponse.ok) {
                    console.log(`file ${file_path} cleared from temp directory.`)
                }
            } else {
                console.error(`Failed to upload ${file_name}`);
            }
        }
    } else {
        console.error('Failed to generate presigned URLs for the dataset');
    }
}