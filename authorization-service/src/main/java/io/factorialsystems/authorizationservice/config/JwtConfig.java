package io.factorialsystems.authorizationservice.config;

import com.nimbusds.jose.jwk.RSAKey;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.*;
import java.security.cert.Certificate;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.util.UUID;

@Slf4j
@Getter
@Component
public class JwtConfig {

    private static final String KEYSTORE_TYPE = "PKCS12";
    private static final String CLASSPATH_PREFIX = "classpath:";

    private final RSAKey rsaKey;

    public JwtConfig(
            @Value("${jwt.keystore.path:classpath:keys/jwt-keystore.p12}") String keystorePath,
            @Value("${jwt.keystore.password:password}") String keystorePassword,
            @Value("${jwt.keystore.alias:authserver}") String keyAlias) {
        this.rsaKey = loadOrGenerateKey(keystorePath, keystorePassword, keyAlias);
    }

    public RSAPublicKey getPublicKey() {
        try {
            return rsaKey.toRSAPublicKey();
        } catch (Exception e) {
            throw new IllegalStateException("Failed to extract RSA public key", e);
        }
    }

    public RSAPrivateKey getPrivateKey() {
        try {
            return rsaKey.toRSAPrivateKey();
        } catch (Exception e) {
            throw new IllegalStateException("Failed to extract RSA private key", e);
        }
    }

    private RSAKey loadOrGenerateKey(String keystorePath, String keystorePassword, String keyAlias) {
        char[] password = keystorePassword.toCharArray();

        if (keystorePath.startsWith(CLASSPATH_PREFIX)) {
            return loadFromClasspath(keystorePath, password, keyAlias);
        }

        Path path = Path.of(keystorePath);
        if (Files.exists(path)) {
            return loadFromFile(path, password, keyAlias);
        }

        return generateKeystore(path, password, keyAlias);
    }

    private RSAKey loadFromClasspath(String keystorePath, char[] password, String keyAlias) {
        String resourcePath = keystorePath.substring(CLASSPATH_PREFIX.length());
        ClassPathResource resource = new ClassPathResource(resourcePath);

        if (!resource.exists()) {
            throw new IllegalStateException(
                    "Keystore not found on classpath: " + resourcePath
                            + ". Run scripts/generate-keystore.sh to generate it.");
        }

        try {
            log.info("Loading RSA key pair from classpath: {}", resourcePath);
            KeyStore keyStore = KeyStore.getInstance(KEYSTORE_TYPE);
            try (InputStream is = resource.getInputStream()) {
                keyStore.load(is, password);
            }
            return extractRsaKey(keyStore, password, keyAlias);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load RSA key pair from classpath: " + resourcePath, e);
        }
    }

    private RSAKey loadFromFile(Path path, char[] password, String keyAlias) {
        try {
            log.info("Loading RSA key pair from keystore: {}", path);
            KeyStore keyStore = KeyStore.getInstance(KEYSTORE_TYPE);
            try (FileInputStream fis = new FileInputStream(path.toFile())) {
                keyStore.load(fis, password);
            }
            return extractRsaKey(keyStore, password, keyAlias);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load RSA key pair from keystore", e);
        }
    }

    private RSAKey generateKeystore(Path path, char[] password, String keyAlias) {
        try {
            log.info("Generating new RSA key pair via keytool and saving to: {}", path);

            Path parent = path.getParent();
            if (parent != null) {
                Files.createDirectories(parent);
            }

            String storepass = new String(password);
            ProcessBuilder pb = new ProcessBuilder(
                    "keytool",
                    "-genkeypair",
                    "-alias", keyAlias,
                    "-keyalg", "RSA",
                    "-keysize", "2048",
                    "-sigalg", "SHA256withRSA",
                    "-storetype", KEYSTORE_TYPE,
                    "-keystore", path.toAbsolutePath().toString(),
                    "-storepass", storepass,
                    "-keypass", storepass,
                    "-dname", "CN=ChatCraft JWT Signing Key",
                    "-validity", "3650"
            );
            pb.inheritIO();

            Process process = pb.start();
            int exitCode = process.waitFor();
            if (exitCode != 0) {
                throw new IllegalStateException("keytool exited with code " + exitCode);
            }

            return loadFromFile(path, password, keyAlias);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to generate keystore", e);
        }
    }

    private RSAKey extractRsaKey(KeyStore keyStore, char[] password, String keyAlias) throws Exception {
        Key key = keyStore.getKey(keyAlias, password);
        if (!(key instanceof RSAPrivateKey privateKey)) {
            throw new IllegalStateException("Key alias '" + keyAlias + "' is not an RSA private key");
        }

        Certificate cert = keyStore.getCertificate(keyAlias);
        RSAPublicKey publicKey = (RSAPublicKey) cert.getPublicKey();

        return new RSAKey.Builder(publicKey)
                .privateKey(privateKey)
                .keyID(UUID.nameUUIDFromBytes(publicKey.getEncoded()).toString())
                .build();
    }
}
