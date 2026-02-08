package io.factorialsystems.authorizationservice.service;

import io.factorialsystems.authorizationservice.dto.request.*;
import io.factorialsystems.authorizationservice.dto.response.AuthResponse;
import io.factorialsystems.authorizationservice.dto.response.UserDto;
import io.factorialsystems.authorizationservice.exception.BadRequestException;
import io.factorialsystems.authorizationservice.exception.ConflictException;
import io.factorialsystems.authorizationservice.exception.NotFoundException;
import io.factorialsystems.authorizationservice.model.Organization;
import io.factorialsystems.authorizationservice.model.PasswordResetToken;
import io.factorialsystems.authorizationservice.model.RefreshToken;
import io.factorialsystems.authorizationservice.model.User;
import io.factorialsystems.authorizationservice.repository.OrganizationRepository;
import io.factorialsystems.authorizationservice.repository.PasswordResetTokenRepository;
import io.factorialsystems.authorizationservice.repository.RefreshTokenRepository;
import io.factorialsystems.authorizationservice.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final OrganizationRepository organizationRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordResetTokenRepository passwordResetTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    @Transactional
    public AuthResponse register(RegisterRequest request) {
        // Check if email is already registered
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new ConflictException("Email is already registered");
        }

        // Generate slug from org name if not provided
        String slug = request.getOrgSlug();
        if (slug == null || slug.isBlank()) {
            slug = slugify(request.getOrgName());
        } else {
            slug = slugify(slug);
        }

        // Ensure slug uniqueness
        String baseSlug = slug;
        int counter = 1;
        while (organizationRepository.existsBySlug(slug)) {
            slug = baseSlug + "-" + counter;
            counter++;
        }

        // Create organization
        Organization organization = Organization.builder()
                .name(request.getOrgName())
                .slug(slug)
                .email(request.getEmail())
                .build();

        organization = organizationRepository.save(organization);

        // Create user with owner role
        User user = User.builder()
                .organization(organization)
                .email(request.getEmail())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .firstName(request.getFirstName())
                .lastName(request.getLastName())
                .role("owner")
                .status("active")
                .emailVerifiedAt(OffsetDateTime.now())
                .lastLoginAt(OffsetDateTime.now())
                .build();

        user = userRepository.save(user);

        log.info("Registered new user {} for organization {}", user.getEmail(), organization.getSlug());

        return generateAuthResponse(user);
    }

    @Transactional
    public AuthResponse login(LoginRequest request) {
        // Authenticate using Spring Security
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword())
        );

        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new NotFoundException("User not found"));

        // Update last login timestamp
        user.setLastLoginAt(OffsetDateTime.now());
        userRepository.save(user);

        log.info("User {} logged in successfully", user.getEmail());

        return generateAuthResponse(user);
    }

    @Transactional
    public AuthResponse refreshToken(RefreshTokenRequest request) {
        String tokenHash = jwtService.hashToken(request.getRefreshToken());

        RefreshToken storedToken = refreshTokenRepository.findByTokenHash(tokenHash)
                .orElseThrow(() -> new BadRequestException("Invalid refresh token"));

        if (!storedToken.isValid()) {
            throw new BadRequestException("Refresh token is expired or revoked");
        }

        // Revoke old refresh token
        storedToken.setRevokedAt(OffsetDateTime.now());
        refreshTokenRepository.save(storedToken);

        User user = storedToken.getUser();
        log.info("Refreshing token for user {}", user.getEmail());

        return generateAuthResponse(user);
    }

    @Transactional
    public void forgotPassword(ForgotPasswordRequest request) {
        userRepository.findByEmail(request.getEmail()).ifPresent(user -> {
            // Generate reset token
            String plainToken = UUID.randomUUID().toString();
            String tokenHash = jwtService.hashToken(plainToken);

            PasswordResetToken resetToken = PasswordResetToken.builder()
                    .user(user)
                    .tokenHash(tokenHash)
                    .expiresAt(OffsetDateTime.now().plusHours(1))
                    .build();

            passwordResetTokenRepository.save(resetToken);

            // TODO: Send email with reset link containing plainToken
            log.info("Password reset token generated for user {}. Token: {} (remove in production)", user.getEmail(), plainToken);
        });

        // Always return success to prevent email enumeration
    }

    @Transactional
    public void resetPassword(ResetPasswordRequest request) {
        String tokenHash = jwtService.hashToken(request.getToken());

        PasswordResetToken resetToken = passwordResetTokenRepository.findByTokenHash(tokenHash)
                .orElseThrow(() -> new BadRequestException("Invalid or expired reset token"));

        if (!resetToken.isValid()) {
            throw new BadRequestException("Invalid or expired reset token");
        }

        // Update password
        User user = resetToken.getUser();
        user.setPasswordHash(passwordEncoder.encode(request.getNewPassword()));
        userRepository.save(user);

        // Mark token as used
        resetToken.setUsedAt(OffsetDateTime.now());
        passwordResetTokenRepository.save(resetToken);

        log.info("Password reset successfully for user {}", user.getEmail());
    }

    @Transactional(readOnly = true)
    public UserDto getCurrentUser(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new NotFoundException("User not found"));

        return toUserDto(user);
    }

    @Transactional(readOnly = true)
    public UserDto getUserByEmail(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new NotFoundException("User not found with email: " + email));

        return toUserDto(user);
    }

    private AuthResponse generateAuthResponse(User user) {
        // Generate access token (JWT)
        String accessToken = jwtService.generateAccessToken(user);

        // Generate refresh token (opaque, stored as hash)
        String plainRefreshToken = jwtService.generateRefreshToken();
        String refreshTokenHash = jwtService.hashToken(plainRefreshToken);

        RefreshToken refreshTokenEntity = RefreshToken.builder()
                .user(user)
                .tokenHash(refreshTokenHash)
                .expiresAt(OffsetDateTime.now().plusDays(jwtService.getRefreshTokenTtlDays()))
                .build();

        refreshTokenRepository.save(refreshTokenEntity);

        return AuthResponse.builder()
                .accessToken(accessToken)
                .refreshToken(plainRefreshToken)
                .tokenType("Bearer")
                .expiresIn(jwtService.getAccessTokenTtlSeconds())
                .user(toUserDto(user))
                .build();
    }

    private UserDto toUserDto(User user) {
        return UserDto.builder()
                .id(user.getId())
                .email(user.getEmail())
                .firstName(user.getFirstName())
                .lastName(user.getLastName())
                .role(user.getRole())
                .status(user.getStatus())
                .organizationId(user.getOrganization().getId())
                .organizationName(user.getOrganization().getName())
                .createdAt(user.getCreatedAt())
                .build();
    }

    private String slugify(String input) {
        if (input == null) {
            return "";
        }
        return input
                .toLowerCase()
                .trim()
                .replaceAll("[^a-z0-9\\s-]", "")
                .replaceAll("[\\s]+", "-")
                .replaceAll("-{2,}", "-")
                .replaceAll("^-|-$", "");
    }
}
