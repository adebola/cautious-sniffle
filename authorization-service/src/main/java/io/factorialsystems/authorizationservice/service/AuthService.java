package io.factorialsystems.authorizationservice.service;

import io.factorialsystems.authorizationservice.dto.request.ForgotPasswordRequest;
import io.factorialsystems.authorizationservice.dto.request.RegisterRequest;
import io.factorialsystems.authorizationservice.dto.request.ResetPasswordRequest;
import io.factorialsystems.authorizationservice.dto.response.UserDto;
import io.factorialsystems.authorizationservice.exception.BadRequestException;
import io.factorialsystems.authorizationservice.exception.ConflictException;
import io.factorialsystems.authorizationservice.exception.NotFoundException;
import io.factorialsystems.authorizationservice.model.Organization;
import io.factorialsystems.authorizationservice.model.PasswordResetToken;
import io.factorialsystems.authorizationservice.model.User;
import io.factorialsystems.authorizationservice.repository.OrganizationRepository;
import io.factorialsystems.authorizationservice.repository.PasswordResetTokenRepository;
import io.factorialsystems.authorizationservice.repository.UserRepository;
import io.factorialsystems.authorizationservice.util.TokenHashUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
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
    private final PasswordResetTokenRepository passwordResetTokenRepository;
    private final PasswordEncoder passwordEncoder;

    @Transactional
    public UserDto register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new ConflictException("Email is already registered");
        }

        String slug = request.getOrgSlug();
        if (slug == null || slug.isBlank()) {
            slug = slugify(request.getOrgName());
        } else {
            slug = slugify(slug);
        }

        String baseSlug = slug;
        int counter = 1;
        while (organizationRepository.existsBySlug(slug)) {
            slug = baseSlug + "-" + counter;
            counter++;
        }

        Organization organization = Organization.builder()
                .name(request.getOrgName())
                .slug(slug)
                .email(request.getEmail())
                .build();

        organization = organizationRepository.save(organization);

        User user = User.builder()
                .organization(organization)
                .email(request.getEmail())
                .passwordHash(passwordEncoder.encode(request.getPassword()))
                .firstName(request.getFirstName())
                .lastName(request.getLastName())
                .role("owner")
                .status("active")
                .emailVerifiedAt(OffsetDateTime.now())
                .build();

        user = userRepository.save(user);

        log.info("Registered new user {} for organization {}", user.getEmail(), organization.getSlug());

        return toUserDto(user);
    }

    @Transactional
    public void forgotPassword(ForgotPasswordRequest request) {
        userRepository.findByEmail(request.getEmail()).ifPresent(user -> {
            String plainToken = UUID.randomUUID().toString();
            String tokenHash = TokenHashUtil.hashToken(plainToken);

            PasswordResetToken resetToken = PasswordResetToken.builder()
                    .user(user)
                    .tokenHash(tokenHash)
                    .expiresAt(OffsetDateTime.now().plusHours(1))
                    .build();

            passwordResetTokenRepository.save(resetToken);

            // TODO: Send email with reset link containing plainToken
            log.info("Password reset token generated for user {}. Token: {} (remove in production)", user.getEmail(), plainToken);
        });
    }

    @Transactional
    public void resetPassword(ResetPasswordRequest request) {
        String tokenHash = TokenHashUtil.hashToken(request.getToken());

        PasswordResetToken resetToken = passwordResetTokenRepository.findByTokenHash(tokenHash)
                .orElseThrow(() -> new BadRequestException("Invalid or expired reset token"));

        if (!resetToken.isValid()) {
            throw new BadRequestException("Invalid or expired reset token");
        }

        User user = resetToken.getUser();
        user.setPasswordHash(passwordEncoder.encode(request.getNewPassword()));
        userRepository.save(user);

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
