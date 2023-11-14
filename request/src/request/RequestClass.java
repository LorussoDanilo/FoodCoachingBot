package request;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class RequestClass {
    public static void main(String[] args) throws IOException {
        try {
            // URL del server al quale inviare la richiesta POST
            URL url = new URL("http://127.0.0.1:5000/upload"); // Sostituisci con l'URL effettivo

            // Apre una connessione HttpURLConnection
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();

            // Imposta il metodo HTTP su POST
            connection.setRequestMethod("POST");

            // Imposta il tipo di contenuto come multipart/form-data
            String boundary = "----Boundary";
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);

            // Abilita l'invio di dati tramite la connessione
            connection.setDoOutput(true);

            // Crea il corpo della richiesta
            String CRLF = "\r\n";
            DataOutputStream request = new DataOutputStream(connection.getOutputStream());

            // Aggiunge il campo del file
            request.writeBytes("--" + boundary + CRLF);
            request.writeBytes("Content-Disposition: form-data; name=\"file\"; filename=\"pasta-al-forno.jpg\"" + CRLF);
            request.writeBytes("Content-Type: image/jpeg" + CRLF);
            request.writeBytes(CRLF);

            // Legge il contenuto del file e lo scrive nel corpo della richiesta
            FileInputStream fileInputStream = new FileInputStream("C:\\Users\\Danilo Lorusso\\Documents\\FoodCoaching\\request\\src\\request\\pasta-al-forno.jpg"); // Sostituisci con il percorso effettivo
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = fileInputStream.read(buffer)) != -1) {
                request.write(buffer, 0, bytesRead);
            }

            fileInputStream.close();

            // Chiude il corpo della richiesta
            request.writeBytes(CRLF);
            request.writeBytes("--" + boundary + "--" + CRLF);

            // Ottiene la risposta dal server
            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                // Legge la risposta dallo stream di input
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()))) {
                    String line;
                    StringBuilder response = new StringBuilder();
                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }

                    // Stampa la risposta
                    System.out.println("Risposta del server: " + response.toString());
                }
            } else {
                // Gestisci l'errore
                // Puoi leggere il messaggio di errore dallo stream di errore
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getErrorStream()))) {
                    String line;
                    StringBuilder errorResponse = new StringBuilder();
                    while ((line = reader.readLine()) != null) {
                        errorResponse.append(line);
                    }

                    // Stampa il messaggio di errore
                    System.err.println("Errore: " + errorResponse.toString());
                }
            }

            // Chiude la connessione
            connection.disconnect();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
