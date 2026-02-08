package io.factorialsystems.authorizationservice.service;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.JWSSigner;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.crypto.RSASSAVerifier;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import io.factorialsystems.authorizationservice.config.JwtConfig;
import io.factorialsystems.authorizationservice.model.User;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.text.ParseException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Date;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class JwtService {

    private static final long ACCESS_TOKEN_TTL_MINUTES = 15;
    private static final long REFRESH_TOKEN_TTL_DAYS = 7;

    private final JWSSigner jwsSigner;
    private final RSASSAVerifier jwtVerifier;
    private final JwtConfig jwtConfig;

    public JwtService(JwtConfig jwtConfig) {
        this.jwtConfig = jwtConfig;
        try {
            this.jwsSigner = new RSASSASigner(jwtConfig.getPrivateKey());
            this.jwtVerifier = new RSASSAVerifier(jwtConfig.getPublicKey());
        } catch (Exception e) {
            throw new IllegalStateException("Failed to initialize JWT signer/verifier", e);
        }
    }

    public String generateAccessToken(User user) {
        try {
            Instant now = Instant.now();
            Instant expiry = now.plus(ACCESS_TOKEN_TTL_MINUTES, ChronoUnit.MINUTES);

            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                    .subject(user.getId().toString())
                    .issuer("http://localhost:8081")
                    .claim("email", user.getEmail())
                    .claim("org_id", user.getOrganization().getId().toString())
                    .claim("org_slug", user.getOrganization().getSlug())
                    .claim("role", user.getRole())
                    .issueTime(Date.from(now))
                    .expirationTime(Date.from(expiry))
                    .jwtID(UUID.randomUUID().toString())
                    .build();

            JWSHeader header = new JWSHeader.Builder(JWSAlgorithm.RS256)
                    .keyID(jwtConfig.getRsaKey().getKeyID())
                    .build();

            SignedJWT signedJWT = new SignedJWT(header, claims);
            signedJWT.sign(jwsSigner);

            return signedJWT.serialize();
        } catch (JOSEException e) {
            throw new IllegalStateException("Failed to generate access token", e);
        }
    }

    public String generateRefreshToken() {
        return UUID.randomUUID().toString();
    }

    public long getAccessTokenTtlSeconds() {
        return ACCESS_TOKEN_TTL_MINUTES * 60;
    }

    public long getRefreshTokenTtlDays() {
        return REFRESH_TOKEN_TTL_DAYS;
    }

    public String hashToken(String token) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 algorithm not available", e);
        }
    }

    public boolean validateToken(String token) {
        try {
            SignedJWT signedJWT = SignedJWT.parse(token);
            if (!signedJWT.verify(jwtVerifier)) {
                return false;
            }
            Date expirationTime = signedJWT.getJWTClaimsSet().getExpirationTime();
            return expirationTime != null && expirationTime.after(new Date());
        } catch (ParseException | JOSEException e) {
            log.debug("Token validation failed: {}", e.getMessage());
            return false;
        }
    }

    public Map<String, Object> extractClaims(String token) {
        try {
            SignedJWT signedJWT = SignedJWT.parse(token);
            JWTClaimsSet claimsSet = signedJWT.getJWTClaimsSet();
            return claimsSet.getClaims();
        } catch (ParseException e) {
            throw new IllegalArgumentException("Invalid JWT token", e);
        }
    }

    public String extractSubject(String token) {
        try {
            SignedJWT signedJWT = SignedJWT.parse(token);
            return signedJWT.getJWTClaimsSet().getSubject();
        } catch (ParseException e) {
            throw new IllegalArgumentException("Invalid JWT token", e);
        }
    }
}
