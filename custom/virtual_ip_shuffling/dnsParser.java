import java.nio.ByteBuffer;
import java.util.Arrays;

public class DNSParser {
    public static void parseDnsResponse(byte[] dnsPayload) {
        ByteBuffer buffer = ByteBuffer.wrap(dnsPayload);

        // Extract DNS header (first 12 bytes)
        int transactionId = buffer.getShort() & 0xFFFF;
        int flags = buffer.getShort() & 0xFFFF;
        int questionCount = buffer.getShort() & 0xFFFF;
        int answerCount = buffer.getShort() & 0xFFFF;
        int authorityCount = buffer.getShort() & 0xFFFF;
        int additionalCount = buffer.getShort() & 0xFFFF;

        System.out.println("Transaction ID: " + transactionId);
        System.out.println("Flags: " + Integer.toBinaryString(flags));
        System.out.println("Questions: " + questionCount);
        System.out.println("Answers: " + answerCount);

        // Read the Question Section
        System.out.print("Query Domain: ");
        while (true) {
            int labelLength = buffer.get() & 0xFF;
            if (labelLength == 0) break; // End of domain name

            byte[] label = new byte[labelLength];
            buffer.get(label);
            System.out.print(new String(label) + ".");
        }
        System.out.println();

        int queryType = buffer.getShort() & 0xFFFF;
        int queryClass = buffer.getShort() & 0xFFFF;
        System.out.println("Query Type: " + queryType);
        System.out.println("Query Class: " + queryClass);

        // Read the Answer Section (assuming an A record response)
        if (answerCount > 0) {
            buffer.getShort(); // Name (pointer)
            int answerType = buffer.getShort() & 0xFFFF;
            int answerClass = buffer.getShort() & 0xFFFF;
            int ttl = buffer.getInt();
            int dataLength = buffer.getShort() & 0xFFFF;

            System.out.println("Answer Type: " + answerType);
            System.out.println("Answer Class: " + answerClass);
            System.out.println("TTL: " + ttl);
            System.out.println("Data Length: " + dataLength);

            // Read the answer IP (last 4 bytes for A record)
            byte[] ipBytes = new byte[4];
            buffer.get(ipBytes);
            System.out.println("Answer IP: " +
                    (ipBytes[0] & 0xFF) + "." +
                    (ipBytes[1] & 0xFF) + "." +
                    (ipBytes[2] & 0xFF) + "." +
                    (ipBytes[3] & 0xFF));
        }
    }

    public static void main(String[] args) {
        byte[] dnsPayload = {66, -30, -123, -128, 0, 1, 0, 1, 0, 0, 0, 0, 
                             3, 97, 98, 99, 3, 99, 111, 109, 0, 0, 1, 0, 1, 
                             -64, 12, 0, 1, 0, 1, 0, 0, 0, 0, 0, 4, -64, -88, 0, 125};
        parseDnsResponse(dnsPayload);
    }
}
